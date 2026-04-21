from enum import Enum

class EstadoCotizacion(str, Enum):
    """
    Estados posibles de una cotización con lógica de negocio encapsulada.
    """
    BORRADOR = "borrador"
    EMITIDA = "emitida"
    MODIFICADA = "modificada"
    PROGRAMADA = "programada"
    FINALIZADA = "finalizada"
    CANCELADA = "cancelada"

    @property
    def es_editable(self) -> bool:
        """Determina si la cotización puede ser editada."""
        return self in (EstadoCotizacion.BORRADOR, EstadoCotizacion.EMITIDA)

    @property
    def es_versionable(self) -> bool:
        """Determina si se debe crear una nueva versión al modificar."""
        return self in (EstadoCotizacion.BORRADOR, EstadoCotizacion.EMITIDA)

    @property
    def permite_crear_ot(self) -> bool:
        """Determina si la cotización puede generar una Orden de Trabajo."""
        return self in (EstadoCotizacion.EMITIDA, EstadoCotizacion.PROGRAMADA)

    @property
    def esta_bloqueada(self) -> bool:
        """Determina si la cotización está bloqueada para cambios estructurales."""
        return self in (
            EstadoCotizacion.MODIFICADA,
            EstadoCotizacion.PROGRAMADA,
            EstadoCotizacion.FINALIZADA,
            EstadoCotizacion.CANCELADA
        )

class EstadoViatico(str, Enum):
    """Estados para el flujo de viáticos."""
    BORRADOR = "borrador"
    SOLICITADO = "solicitado"
    APROBADO = "aprobado"
    PAGADO = "pagado"
    CANCELADO = "cancelado"
