"""Constantes de ciclo de vida del viático."""
from enum import Enum

class EstadoViatico(str, Enum):
    BORRADOR = "borrador"
    SOLICITADO = "solicitado"
    APROBADO = "aprobado"
    CANCELADO = "cancelado"
    FINALIZADO = "finalizada"

    @property
    def es_editable(self) -> bool:
        """Determina si el viático puede ser editado."""
        return self in (EstadoViatico.BORRADOR, EstadoViatico.SOLICITADO, EstadoViatico.APROBADO)

    @property
    def es_cancelable(self) -> bool:
        """Determina si el viático puede ser cancelado."""
        return self != EstadoViatico.CANCELADO
