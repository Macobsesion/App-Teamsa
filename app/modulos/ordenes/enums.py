from enum import Enum

class EstadoOrden(str, Enum):
    """
    Estados posibles de una Orden de Trabajo.
    """
    PROGRAMADA = "programada"
    EN_CURSO = "en_curso"
    FINALIZADA = "finalizada"
    CANCELADA = "cancelada"

    @property
    def es_editable(self) -> bool:
        """Determina si la orden puede ser editada (fechas, notas)."""
        return self in (EstadoOrden.PROGRAMADA, EstadoOrden.EN_CURSO)

    @property
    def es_cancelable(self) -> bool:
        """Determina si la orden puede ser cancelada."""
        return self in (EstadoOrden.PROGRAMADA, EstadoOrden.EN_CURSO)
        
    @property
    def esta_activa(self) -> bool:
        """Determina si la orden está en curso o programada (no finalizada/cancelada)."""
        return self in (EstadoOrden.PROGRAMADA, EstadoOrden.EN_CURSO)
