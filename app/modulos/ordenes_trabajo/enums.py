from enum import Enum

class EstadoOrden(str, Enum):
    """
    Estados posibles de una Orden de Trabajo.
    """
    PROGRAMADA = "programada"
    FINALIZADA = "finalizada"
    CANCELADA = "cancelada"

    @property
    def es_editable(self) -> bool:
        """Determina si la orden puede ser editada (fechas, notas)."""
        return self == EstadoOrden.PROGRAMADA

    @property
    def es_cancelable(self) -> bool:
        """Determina si la orden puede ser cancelada."""
        return self == EstadoOrden.PROGRAMADA
        
    @property
    def esta_activa(self) -> bool:
        """Determina si la orden está programada (no finalizada/cancelada)."""
        return self == EstadoOrden.PROGRAMADA


class EstadoConceptoOT(str, Enum):
    """
    Estados de un concepto dentro de una Orden de Trabajo.
    
    El flujo es unidireccional: pendiente → completado (irreversible).
    Un concepto completado no puede volver a pendiente.
    """
    PENDIENTE = "pendiente"
    COMPLETADO = "completado"
