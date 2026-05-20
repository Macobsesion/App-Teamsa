import pytest
from app.modulos.cotizaciones.enums import EstadoCotizacion
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion

def test_estado_cotizacion_propiedades():
    """Verifica las propiedades del Enum EstadoCotizacion."""
    assert EstadoCotizacion.BORRADOR.es_editable is True
    assert EstadoCotizacion.EMITIDA.es_editable is True
    assert EstadoCotizacion.MODIFICADA.es_editable is False
    assert EstadoCotizacion.FINALIZADA.es_editable is False
    
    assert EstadoCotizacion.EMITIDA.permite_crear_ot is True
    assert EstadoCotizacion.BORRADOR.permite_crear_ot is True  # Regla actual permite en borrador
    assert EstadoCotizacion.PROGRAMADA.permite_crear_ot is True

def test_cotizacion_propiedades_estado():
    """Verifica que el modelo Cotizacion delegue correctamente al estado."""
    c = Cotizacion(estado=EstadoCotizacion.BORRADOR.value)
    assert c.es_editable is True
    assert c.puede_crear_ot is True
    
    c.estado = EstadoCotizacion.EMITIDA.value
    assert c.es_editable is True
    assert c.puede_crear_ot is True
    
    c.estado = EstadoCotizacion.FINALIZADA.value
    assert c.es_editable is False
    assert c.puede_crear_ot is False
