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
    campos_busqueda = {"nombre": "icontains"}
    orden_por_defecto = ("nombre", False)
    
    def obtener_por_nombre(self, nombre: str) -> Cliente | None:
        """Busca un cliente por nombre exacto."""
        return self.db.query(Cliente).filter(Cliente.nombre == nombre).first()
