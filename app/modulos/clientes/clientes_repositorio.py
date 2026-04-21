"""Repositorio para clientes."""
from sqlmodel import Session  # type: ignore

from app.base.repositorio import RepositorioCRUD
from app.modulos.clientes.clientes_modelo import Cliente


class RepositorioCliente(RepositorioCRUD[Cliente]):
    """Repositorio de clientes con búsqueda por nombre."""
    
    modelo = Cliente
    campos_filtrables = {"activo"}
    campos_actualizables = {
        "nombre", "rfc", "razon_social", "contacto", "email",
        "telefono", "direccion", "ciudad", "estado", "cp",
        "activo", "notas", "modificado_por"
    }
    campos_busqueda = {"nombre": "icontains", "rfc": "icontains", "email": "icontains"}
    orden_por_defecto = ("nombre", False)

    def _pre_guardar(self, entidad: Cliente, es_nuevo: bool) -> None:
        """Validar integridad lógica al inactivar."""
        if not es_nuevo and not entidad.activo:
            from sqlmodel import select, or_
            from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
            from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
            from app.base.excepciones import ReglaNegocioError
            
            # Verificar Cotizaciones activas
            cot_activas = self.db.exec(
                select(Cotizacion).where(
                    Cotizacion.cliente_id == entidad.id,
                    Cotizacion.estado.notin_(["cancelada", "rechazada", "modificada"])
                )
            ).first()
            if cot_activas:
                raise ReglaNegocioError(f"No se puede inactivar: El cliente tiene cotizaciones activas (ej: {cot_activas.numero}).")

            # Verificar OTs activas
            ots_activas = self.db.exec(
                select(OrdenTrabajo).where(
                    OrdenTrabajo.cliente_id == entidad.id,
                    OrdenTrabajo.estado != "cancelada"
                )
            ).first()
            if ots_activas:
                raise ReglaNegocioError(f"No se puede inactivar: El cliente tiene Órdenes de Trabajo activas (ej: {ots_activas.numero_ot}).")

    def _validar_eliminacion(self, entidad: Cliente) -> None:
        """No permitir eliminar físicamente si tiene uso en documentos."""
        from sqlmodel import select
        from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
        from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
        from app.modulos.viaticos.viaticos_modelo import Viatico
        from app.base.excepciones import ReglaNegocioError
        
        # 1. Verificar Cotizaciones
        uso_cot = self.db.exec(select(Cotizacion).where(Cotizacion.cliente_id == entidad.id)).first()
        if uso_cot:
            raise ReglaNegocioError(f"No se puede eliminar el cliente '{entidad.nombre}': Está en uso en la cotización {uso_cot.numero}.")

        # 2. Verificar Órdenes de Trabajo
        uso_ot = self.db.exec(select(OrdenTrabajo).where(OrdenTrabajo.cliente_id == entidad.id)).first()
        if uso_ot:
            raise ReglaNegocioError(f"No se puede eliminar el cliente '{entidad.nombre}': Está en uso en la orden de trabajo {uso_ot.numero_ot}.")

        # 3. Verificar Viáticos
        uso_via = self.db.exec(select(Viatico).where(Viatico.cliente_id == entidad.id)).first()
        if uso_via:
            raise ReglaNegocioError(f"No se puede eliminar el cliente '{entidad.nombre}': Está en uso en viáticos registrados.")
