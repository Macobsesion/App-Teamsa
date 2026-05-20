import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
from app.modulos.ordenes_trabajo.enums import EstadoOrden
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.clientes.clientes_modelo import Cliente


def test_estado_orden_propiedades():
    """Verifica las propiedades del Enum EstadoOrden."""
    assert EstadoOrden.PROGRAMADA.es_editable is True
    assert EstadoOrden.EN_CURSO.es_editable is True
    assert EstadoOrden.FINALIZADA.es_editable is False
    assert EstadoOrden.CANCELADA.es_editable is False

    assert EstadoOrden.PROGRAMADA.esta_activa is True
    assert EstadoOrden.FINALIZADA.esta_activa is False


def test_orden_propiedades_estado():
    """Verifica que el modelo OrdenTrabajo delegue correctamente al estado."""
    orden = OrdenTrabajo(estado=EstadoOrden.PROGRAMADA.value)

    assert orden.es_editable is True
    assert orden.es_cancelable is True

    orden.estado = EstadoOrden.FINALIZADA.value
    assert orden.es_editable is False
    assert orden.es_cancelable is False


def test_factory_method_snapshot():
    """Verifica que el Factory Method capture correctamente el snapshot de datos."""
    # Mock de datos
    cliente = Cliente(
        id=1,
        nombre="Empresa ABC",
        direccion="Calle Falsa 123",
        contacto="Juan Pérez"
    )
    cotizacion = Cotizacion(id=10, cliente=cliente, cliente_id=1)

    fecha = date(2025, 1, 30)

    # Mock del generador de folio (Strategy Pattern)
    generador_folio = MagicMock()
    generador_folio.generar.return_value = "OT-10-20250130"

    orden = OrdenTrabajo.crear_desde_cotizacion(
        cotizacion=cotizacion,
        fecha_programada=fecha,
        hora_programada="10:00",
        duracion=2,
        usuario_id="user123",
        generador_folio=generador_folio
    )

    # Simular persistencia
    orden.id = 10
    orden.asignar_folio(generador_folio)

    # Verificar Snapshot
    assert orden.cliente_nombre == "Empresa ABC"
    assert orden.domicilio == "Calle Falsa 123"
    assert orden.contacto == "Juan Pérez"

    # Verificar OT generada
    assert orden.numero_ot == "OT-10-20250130"
    assert orden.estado == EstadoOrden.PROGRAMADA.value

    # Verificar que el generador fue llamado correctamente
    generador_folio.generar.assert_called_once()
