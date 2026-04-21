"""Servicio de Dominio para Órdenes de Compra."""
from decimal import Decimal
from datetime import date
from sqlmodel import Session
import uuid
from typing import Any, Dict, List

from app.base.servicios import ServicioDominio, FabricaImpuestos
from app.base.folios import EstrategiaFolioFechaId
from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra, DetalleOrdenCompra
from app.modulos.ordenes_compra.ordenes_compra_repositorio import RepositorioOrdenCompra

from app.base.servicios_documentos import ServicioDocumentoFinanciero

class ServicioCreacionOrdenCompra(ServicioDocumentoFinanciero[OrdenCompra, DetalleOrdenCompra]):

    def _crear_instancia_cabecera(self, data: dict) -> OrdenCompra:
        """Implementación del paso: Crear instancia base."""
        from app.modulos.proveedores.proveedores_modelo import Proveedor
        proveedor_id = data['proveedor_id']
        proveedor = self.db.get(Proveedor, proveedor_id)
        if not proveedor:
            from app.base.excepciones import RecursoNoEncontradoError
            raise RecursoNoEncontradoError("Proveedor no encontrado")

        temp_folio = f"TEMP-{uuid.uuid4()}"
        return OrdenCompra(
            proveedor_id=proveedor_id,
            proveedor_nombre=proveedor.nombre,
            proveedor_rfc=proveedor.rfc,
            proveedor_direccion=proveedor.direccion,
            proveedor_ciudad=proveedor.ciudad,
            proveedor_cp=proveedor.cp,
            proveedor_telefono=proveedor.telefono,
            proveedor_email=proveedor.email,
            fecha_emision=date.today(),
            fecha_entrega_estimada=data.get('fecha_entrega') or None,
            metodo_pago=data.get('metodo_pago', 'POR_DEFINIR'),
            forma_pago=data.get('forma_pago', '99'),
            notas=data.get('notas'),
            estado='borrador',
            folio=temp_folio, 
            creado_por=data.get('usuario_id', 'SISTEMA'),
            modificado_por=data.get('usuario_id', 'SISTEMA')
        )

    def _generar_folio_final(self, documento: OrdenCompra) -> str | None:
        """Implementación del paso: Generar Folio."""
        generador = EstrategiaFolioFechaId()
        return generador.generar("OC", documento.id, date.today()) # type: ignore

    def _procesar_detalles(self, documento: OrdenCompra, items_data: list) -> list[DetalleOrdenCompra]:
        """Implementación del paso: Procesar Detalles."""
        detalles_orm = []
        for item in items_data:
            cantidad = Decimal(str(item['cantidad']))
            precio = Decimal(str(item['precio_unitario']))
            desc_pct = Decimal(str(item.get('descuento_porcentaje', '0.00')))
            
            detalle = DetalleOrdenCompra(
                orden_id=documento.id, # type: ignore
                servicio_proveedor_id=item.get('servicio_id'),
                codigo_sku=item.get('codigo_sku') or item.get('codigo', ''),
                descripcion=item['descripcion'],
                unidad=item.get('unidad', 'Pieza'),
                cantidad=cantidad,
                precio_unitario=precio,
                descuento_porcentaje=desc_pct,
                modificado_por=documento.creado_por,
                creado_por=documento.creado_por
            )
            # Usar lógica del mixin
            detalle.calcular_importe()
            detalles_orm.append(detalle)
        return detalles_orm


    def actualizar_completa(self, orden_id: int, data: dict, usuario_id: str) -> OrdenCompra:
        """Actualiza una orden de compra existente usando estrategia de Fusión (Merge)."""
        orden = self.db.get(OrdenCompra, orden_id)
        if not orden:
            from app.base.excepciones import RecursoNoEncontradoError
            raise RecursoNoEncontradoError("Orden de compra no encontrada")

        # 1. Actualizar encabezado
        orden.fecha_entrega_estimada = data.get('fecha_entrega') or orden.fecha_entrega_estimada
        orden.metodo_pago = data.get('metodo_pago', orden.metodo_pago)
        orden.forma_pago = data.get('forma_pago', orden.forma_pago)
        orden.notas = data.get('notas', orden.notas)
        orden.modificado_por = usuario_id

        # Actualizar snapshot del proveedor
        from app.modulos.proveedores.proveedores_modelo import Proveedor
        proveedor = self.db.get(Proveedor, orden.proveedor_id)
        if proveedor:
            orden.proveedor_nombre = proveedor.nombre
            orden.proveedor_rfc = proveedor.rfc
            orden.proveedor_direccion = proveedor.direccion
            orden.proveedor_ciudad = proveedor.ciudad
            orden.proveedor_cp = proveedor.cp

        # 2. Estrategia de Fusión para Detalles (Merge)
        items_request = data.get('items', [])
        detalles_actuales = {d.id: d for d in orden.detalles}
        nuevos_detalles = []
        ids_en_request = set()

        for item_data in items_request:
            item_id = item_data.get('id')
            cantidad = Decimal(str(item_data['cantidad']))
            precio = Decimal(str(item_data['precio_unitario']))
            desc_pct = Decimal(str(item_data.get('descuento_porcentaje', '0.00')))

            if item_id and item_id in detalles_actuales:
                # ACTUALIZAR EXISTENTE
                detalle = detalles_actuales[item_id]
                detalle.cantidad = cantidad
                detalle.precio_unitario = precio
                detalle.descuento_porcentaje = desc_pct
                # Solo actualizar descripción si viene explícitamente y no es nula
                if item_data.get('descripcion'):
                    detalle.descripcion = item_data['descripcion']
                detalle.modificado_por = usuario_id
                ids_en_request.add(item_id)
            else:
                # CREAR NUEVO
                detalle = DetalleOrdenCompra(
                    orden_id=orden.id,
                    servicio_proveedor_id=item_data.get('servicio_id'),
                    codigo_sku=item_data.get('codigo_sku') or item_data.get('codigo', ''),
                    descripcion=item_data['descripcion'],
                    unidad=item_data.get('unidad', 'Pieza'),
                    cantidad=cantidad,
                    precio_unitario=precio,
                    descuento_porcentaje=desc_pct,
                    creado_por=usuario_id,
                    modificado_por=usuario_id
                )
                self.db.add(detalle)
            
            detalle.calcular_importe()
            nuevos_detalles.append(detalle)

        # 3. Eliminar partidas que ya no están en el request
        # IMPORTANTE: Si un ítem del catálogo está inactivo, el UI podría omitirlo.
        # Por ahora, confiamos en el request, pero preservamos si no hay cambios.
        for d_id, d_obj in detalles_actuales.items():
            if d_id not in ids_en_request:
                self.db.delete(d_obj)

        # 4. Recalcular totales
        from app.base.servicios import FabricaImpuestos
        calculadora = FabricaImpuestos.obtener_estrategia("mx_iva_16")
        orden.subtotal = sum(d.importe for d in nuevos_detalles)
        orden.iva = calculadora.calcular(orden.subtotal)
        orden.total = orden.subtotal + orden.iva

        self.db.commit()
        self.db.refresh(orden)
        return orden

    def crear_completa(self, data: dict, usuario_id: str) -> OrdenCompra:
        """
        Wrapper de compatibilidad para el router.
        """
        # Aseguramos que el usuario_id esté en los datos para la cabecera
        data['usuario_id'] = usuario_id
        items = data.get('items', []) or data.get('detalles', [])
        
        return self.crear_documento(data, items)
