"""Repositorio para servicios de proveedores."""
from app.base.repositorio import RepositorioCRUD
from app.modulos.servicios_proveedores.servicios_proveedores_modelo import ServicioProveedor

class RepositorioServicioProveedor(RepositorioCRUD[ServicioProveedor]):
    modelo = ServicioProveedor
    campos_filtrables = {"proveedor_id", "activo", "moneda"}
    campos_busqueda = {"descripcion": "icontains", "codigo_sku": "icontains"}
    campos_actualizables = {
        "proveedor_id", "codigo_sku", "descripcion", 
        "descripcion_detallada", "costo_unitario", "moneda", 
        "unidad", "activo", "modificado_por"
    }

    def _validar_eliminacion(self, entidad: ServicioProveedor) -> None:
        """Verifica si el servicio está siendo usado en Órdenes de Compra."""
        from app.modulos.ordenes_compra.ordenes_compra_modelo import DetalleOrdenCompra
        from app.base.excepciones import ReglaNegocioError
        from sqlmodel import select, func

        # Contar usos en OCs
        statement = select(func.count(DetalleOrdenCompra.id)).where(DetalleOrdenCompra.servicio_proveedor_id == entidad.id)
        conteo = self.db.exec(statement).one()

        if conteo > 0:
            raise ReglaNegocioError(
                f"No se puede eliminar el servicio '{entidad.descripcion}': "
                f"existen {conteo} partidas de Órdenes de Compra vinculadas. "
                "Considere marcarlo como Inactivo en su lugar."
            )
