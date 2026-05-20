"""Constantes de ciclo de vida del viático."""
from enum import Enum

class EstadoViatico(str, Enum):
    BORRADOR = "borrador"
    SOLICITADO = "solicitado"
    APROBADO = "aprobado"
    CANCELADO = "cancelado"
