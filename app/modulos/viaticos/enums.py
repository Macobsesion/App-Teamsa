"""Constantes de ciclo de vida del viático."""
from enum import Enum

class EstadoViatico(str, Enum):
    """
    Estados posibles de un Viático (simplificado).
    
    Estados persistidos en BD: borrador, cancelado, finalizada.
    Estados visuales (calculados dinámicamente): en_curso, fase_final.
    """
    BORRADOR = "borrador"
    SOLICITADO = "solicitado" # Legacy
    APROBADO = "aprobado"     # Legacy
    EN_CURSO = "en_curso"
    FASE_FINAL = "fase_final"
    CANCELADO = "cancelado"
    FINALIZADO = "finalizada"

    @property
    def es_editable(self) -> bool:
        """Determina si el viático puede ser editado."""
        return self == EstadoViatico.BORRADOR

    @property
    def es_cancelable(self) -> bool:
        """Determina si el viático puede ser cancelado."""
        return self not in (EstadoViatico.CANCELADO, EstadoViatico.FINALIZADO)
