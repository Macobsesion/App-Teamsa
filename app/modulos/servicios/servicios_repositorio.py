"""Repositorio para servicios."""
from sqlmodel import Session  # type: ignore

from app.base.repositorio import RepositorioCRUD
from app.modulos.servicios.servicios_modelo import Servicio


class RepositorioServicio(RepositorioCRUD[Servicio]):
    """Repositorio de servicios con búsqueda por clave y descripción."""
    
    modelo = Servicio
    campos_filtrables = {"activo", "tipo"}
    campos_actualizables = {
        "codigo_sat", "codigo_unidad", "clave", "descripcion",
        "tipo", "precio_base", "unidad", "activo", "notas",
        "modificado_por"
    }
    campos_busqueda = {
        "clave": "icontains",
        "descripcion": "icontains"
    }
    orden_por_defecto = ("clave", False)
    
    def obtener_por_clave(self, clave: str) -> Servicio | None:
        """Busca un servicio por clave exacta."""
        return self.db.query(Servicio).filter(Servicio.clave == clave).first()
