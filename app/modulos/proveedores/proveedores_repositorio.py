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
    campos_busqueda = {"nombre": "icontains"}
    orden_por_defecto = ("nombre", False)
    

