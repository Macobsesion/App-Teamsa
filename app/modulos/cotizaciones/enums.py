from enum import Enum

class EstadoCotizacion(str, Enum):
    """
    Estados posibles de una cotización con lógica de negocio encapsulada.
    """
    BORRADOR = "borrador"
    ENVIADA = "enviada"
    MODIFICADA = "modificada"
    PROGRAMADA = "programada"
    FINALIZADA = "finalizada"
    CANCELADA = "cancelada"

    @property
    def es_editable(self) -> bool:
        """Determina si la cotización puede ser editada."""
        return self in (EstadoCotizacion.BORRADOR, EstadoCotizacion.ENVIADA)

    @property
    def es_versionable(self) -> bool:
        """Determina si se debe crear una nueva versión al modificar."""
        return self in (EstadoCotizacion.BORRADOR, EstadoCotizacion.ENVIADA)

    @property
    def permite_crear_ot(self) -> bool:
        """Determina si la cotización puede generar una Orden de Trabajo."""
        return self == EstadoCotizacion.ENVIADA

    @property
    def esta_bloqueada(self) -> bool:
        """Determina si la cotización está bloqueada para cambios."""
        return self in (EstadoCotizacion.MODIFICADA, EstadoCotizacion.PROGRAMADA, EstadoCotizacion.FINALIZADA, EstadoCotizacion.CANCELADA)
