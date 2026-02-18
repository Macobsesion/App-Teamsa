import pytest
from decimal import Decimal
from datetime import date
from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo
from app.modulos.cotizaciones.enums import EstadoCotizacion
from tests.factories import CotizacionFactory, ConceptoCotizacionFactory, ClienteFactory


@pytest.fixture
def cotizacion_con_cliente(session):
    """Crea una cotización con cliente asociado, lista para crear OT."""
    cliente = ClienteFactory(
        nombre="Cliente OT Test",
        direccion="Av. Principal 100",
        contacto="María López"
    )
    session.add(cliente)
    session.flush()

    cot = CotizacionFactory(
        estado=EstadoCotizacion.ENVIADA.value,
        cliente=cliente,
        cliente_id=cliente.id,
        folio="COT-TEST-OT"
    )
    session.add(cot)
    session.flush()

    concepto = ConceptoCotizacionFactory(
        cotizacion=cot,
        cotizacion_id=cot.id,
        importe=Decimal("1000.00")
    )
    session.add(concepto)
    session.commit()
    return cot


def test_crear_ot_desde_cotizacion(admin_client, session, cotizacion_con_cliente):
    """
    Verifica que se puede crear una OT usando el endpoint especializado.
    Endpoint real: POST /api/ordenes/crear-desde-cotizacion
    """
    assert cotizacion_con_cliente.id is not None, "La cotización debe tener ID"

    payload = {
        "cotizacion_id": cotizacion_con_cliente.id,
        "fecha_programada": str(date.today()),
        "hora_programada": "10:00",
        "duracion": 2
    }

    response = admin_client.post("/api/ordenes/crear-desde-cotizacion", json=payload)

    if response.status_code not in [200, 201]:
        print(f"DEBUG OT: {response.status_code} - {response.json()}")

    assert response.status_code in [200, 201]
    data = response.json()
    assert data["cotizacion_id"] == cotizacion_con_cliente.id
    assert "numero_ot" in data


def test_listar_ordenes(admin_client, session):
    """Verifica que el listado de órdenes funcione."""
    response = admin_client.get("/api/ordenes")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_obtener_orden_inexistente(admin_client, session):
    """Verificar 404 para orden que no existe."""
    response = admin_client.get("/api/ordenes/999999")
    assert response.status_code == 404
