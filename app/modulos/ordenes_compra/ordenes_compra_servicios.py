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
            raise ValueError("Proveedor no encontrado")

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
        """Actualiza una orden de compra existente y reemplaza sus detalles."""
        orden = self.db.get(OrdenCompra, orden_id)
        if not orden:
            from app.base.excepciones import RecursoNoEncontradoError
            raise RecursoNoEncontradoError("Orden de compra no encontrada")

        # 1. Actualizar encabezado
        orden.fecha_entrega_estimada = data.get('fecha_entrega') or None
        orden.metodo_pago = data.get('metodo_pago', orden.metodo_pago)
        orden.forma_pago = data.get('forma_pago', orden.forma_pago)
        orden.notas = data.get('notas', orden.notas)
        orden.modificado_por = usuario_id

        # Renovar el snapshot del proveedor al editar/guardar la OC
        from app.modulos.proveedores.proveedores_modelo import Proveedor
        proveedor = self.db.get(Proveedor, orden.proveedor_id)
        if proveedor:
            orden.proveedor_nombre = proveedor.nombre
            orden.proveedor_rfc = proveedor.rfc
            orden.proveedor_direccion = proveedor.direccion
            orden.proveedor_ciudad = proveedor.ciudad
            orden.proveedor_cp = proveedor.cp
            orden.proveedor_telefono = proveedor.telefono
            orden.proveedor_email = proveedor.email

        # 2. Borrar detalles existentes y recrear
        for detalle in orden.detalles:
            self.db.delete(detalle)
        self.db.flush()

        # 3. Crear nuevos detalles
        detalles_orm = []
        calculadora_impuestos = FabricaImpuestos.obtener_estrategia("mx_iva_16")

        for item in data.get('items', []):
            cantidad = Decimal(str(item['cantidad']))
            precio = Decimal(str(item['precio_unitario']))
            desc_pct = Decimal(str(item.get('descuento_porcentaje', '0.00')))

            detalle = DetalleOrdenCompra(
                orden_id=orden.id,
                servicio_proveedor_id=item.get('servicio_id'),
                codigo_sku=item.get('codigo_sku') or item.get('codigo', ''),
                descripcion=item['descripcion'],
                unidad=item.get('unidad', 'Pieza'),
                cantidad=cantidad,
                precio_unitario=precio,
                descuento_porcentaje=desc_pct,
                modificado_por=usuario_id,
                creado_por=usuario_id
            )
            detalle.calcular_importe()
            detalles_orm.append(detalle)
            self.db.add(detalle)

        # 4. Recalcular totales
        subtotal = sum(d.importe for d in detalles_orm)
        orden.subtotal = subtotal
        orden.iva = calculadora_impuestos.calcular(orden.subtotal)
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
