"""Constantes y Enums para Órdenes de Compra."""
from enum import Enum

class EstadoOrdenCompra(str, Enum):
    """
    Estados posibles de una Orden de Compra.
    """
    BORRADOR = "borrador"
    EMITIDA = "emitida"           # Enviada al proveedor
    PARCIALMENTE_RECIBIDA = "parcial"
    RECIBIDA = "recibida"         # Completa
    CANCELADA = "cancelada"

    @property
    def es_editable(self) -> bool:
        """Determina si la OC puede ser editada."""
        return self == EstadoOrdenCompra.BORRADOR

    @property
    def es_cancelable(self) -> bool:
        """Determina si la OC puede ser cancelada."""
        return self not in (EstadoOrdenCompra.CANCELADA, EstadoOrdenCompra.RECIBIDA)
