"""Repositorio para proveedores."""
from sqlmodel import Session  # type: ignore

from app.base.repositorio import RepositorioCRUD
from app.modulos.proveedores.proveedores_modelo import Proveedor


class RepositorioProveedor(RepositorioCRUD[Proveedor]):
    """Repositorio de proveedores con búsqueda por nombre."""
    
    modelo = Proveedor
    campos_filtrables = {"activo", "categoria"}
    campos_actualizables = {
        "nombre", "rfc", "razon_social", "contacto", "email",
        "telefono", "direccion", "ciudad", "estado", "cp",
        "categoria", "activo", "notas", "modificado_por"
    }
    campos_busqueda = {"nombre": "icontains", "rfc": "icontains", "email": "icontains"}
    orden_por_defecto = ("nombre", False)

    def _pre_guardar(self, entidad: Proveedor, es_nuevo: bool) -> None:
        """Validar integridad lógica al inactivar."""
        if not es_nuevo and not entidad.activo:
            from sqlmodel import select
            from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra
            from app.base.excepciones import ReglaNegocioError
            
            # Verificar Ordenes de Compra activas
            oc_activas = self.db.exec(
                select(OrdenCompra).where(
                    OrdenCompra.proveedor_id == entidad.id,
                    OrdenCompra.estado.notin_(["cancelada", "rechazada", "finalizada"])
                )
            ).first()
            if oc_activas:
                raise ReglaNegocioError(f"No se puede inactivar: El proveedor tiene órdenes de compra activas (ej: {oc_activas.numero}).")

    def eliminar(self, entidad_id: int) -> None:
        """No permitir eliminar físicamente si tiene uso en documentos."""
        from sqlmodel import select
        from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra
        from app.base.excepciones import ReglaNegocioError
        
        # 1. Verificar Ordenes de Compra
        uso_oc = self.db.exec(select(OrdenCompra).where(OrdenCompra.proveedor_id == entidad_id)).first()
        if uso_oc:
            raise ReglaNegocioError(f"No se puede eliminar el proveedor: Está en uso en la orden de compra {uso_oc.numero}.")

        return super().eliminar(entidad_id)
    

