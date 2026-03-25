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
