"""Servicio de Dominio para Órdenes de Compra."""
from decimal import Decimal
from datetime import date
from sqlmodel import Session
import uuid
from typing import Any, Dict, List

from app.base.servicios import ServicioDominio, FabricaImpuestos
from app.base.folios import EstrategiaFolioFechaId
from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra, DetalleOrdenCompra
from app.modulos.ordenes_compra.enums import EstadoOrdenCompra
from app.modulos.ordenes_compra.ordenes_compra_repositorio import RepositorioOrdenCompra

from app.base.servicios_documentos import ServicioDocumentoFinanciero

class ServicioCreacionOrdenCompra(ServicioDocumentoFinanciero[OrdenCompra, DetalleOrdenCompra]):
    
    def __init__(self, repo_ordenes: Any, repo_proveedores: Any):
        super().__init__(repo_ordenes)
        self.repo_proveedores = repo_proveedores

    def _crear_instancia_cabecera(self, data: dict) -> OrdenCompra:
        """Implementación del paso: Crear instancia base."""
        proveedor_id = data['proveedor_id']
        proveedor = self.repo_proveedores.obtener_por_id(proveedor_id)
        if not proveedor:
            from app.base.excepciones import RecursoNoEncontradoError
            raise RecursoNoEncontradoError("Proveedor no encontrado")

        temp_folio = f"TEMP-{uuid.uuid4()}"
        orden = OrdenCompra(
            proveedor_id=proveedor_id,
            fecha_emision=date.today(),
            fecha_entrega_estimada=data.get('fecha_entrega') or None,
            metodo_pago=data.get('metodo_pago', 'POR_DEFINIR'),
            forma_pago=data.get('forma_pago', '99'),
            notas=data.get('notas'),
            estado=EstadoOrdenCompra.BORRADOR.value,
            folio=temp_folio, 
            creado_por=data.get('usuario_id', 'SISTEMA'),
            modificado_por=data.get('usuario_id', 'SISTEMA')
        )
        # Usar el Mixin para capturar snapshot de integridad
        orden.capturar_datos_proveedor(proveedor)
        return orden

    def _generar_folio_final(self, documento: OrdenCompra) -> str | None:
        """
        Delega la generación del folio final al repositorio.
        Al retornar None aquí, el ServicioDocumentoFinanciero mantiene el TEMP,
        y el RepositorioOrdenCompra._post_guardar generará el folio real.
        """
        return None

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
        orden = self.repo_documento.obtener_por_id(orden_id)
        if not orden:
            from app.base.excepciones import RecursoNoEncontradoError
            raise RecursoNoEncontradoError("Orden de compra no encontrada")

        # 1. Actualizar encabezado
        orden.fecha_entrega_estimada = data.get('fecha_entrega') or orden.fecha_entrega_estimada
        orden.metodo_pago = data.get('metodo_pago', orden.metodo_pago)
        orden.forma_pago = data.get('forma_pago', orden.forma_pago)
        orden.notas = data.get('notas', orden.notas)
        orden.modificado_por = usuario_id

        # Actualizar snapshot del proveedor usando el Mixin
        proveedor = self.repo_proveedores.obtener_por_id(orden.proveedor_id)
        if proveedor:
            orden.capturar_datos_proveedor(proveedor)

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
        orden.recalcular_totales()

        # DELEGADO AL REPOSITORIO: Garantiza triggers y eventos de dominio
        return self.repo_documento.guardar(orden)

    def crear_completa(self, data: dict, usuario_id: str) -> OrdenCompra:
        """
        Wrapper de compatibilidad para el router.
        """
        # Aseguramos que el usuario_id esté en los datos para la cabecera
        data['usuario_id'] = usuario_id
        items = data.get('items', []) or data.get('detalles', [])
        
        return self.crear_documento(data, items)
