import pytest
import uuid
from decimal import Decimal
from app.modulos.servicios.servicios_modelo import Servicio
from tests.factories import ServicioFactory


def test_listar_servicios(admin_client, session):
    """Verifica listado de servicios."""
    for i in range(5):
        unique = f"LST-{uuid.uuid4().hex[:6]}"
        s = ServicioFactory(clave=unique)
        session.add(s)
    session.commit()

    response = admin_client.get("/api/servicios")
    assert response.status_code == 200
    assert len(response.json()) >= 5


def test_crear_servicio_valido(admin_client, session):
    """Verifica creación de servicio vía API."""
    unique = str(uuid.uuid4())[:8]
    payload = {
        "clave": f"SRV-{unique}",
        "descripcion": "Nuevo Servicio",
        "codigo_sat": "81111500",
        "unidad": "Servicio",
        "codigo_unidad": "E48",
        "precio_base": 1500.50,
        "area": "Taller",
        "activo": True
    }

    response = admin_client.post("/api/servicios", json=payload)
    if response.status_code != 200:
        print(f"DEBUG: Error crear servicio: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["clave"] == payload["clave"]
    assert Decimal(str(data["precio_base"])) == Decimal("1500.50")


def test_actualizar_precio(admin_client, session):
    """Verifica actualización de precio de servicio."""
    servicio = ServicioFactory(precio_base=Decimal("100.00"))
    session.add(servicio)
    session.flush()
    session.commit()

    assert servicio.id is not None, "El servicio debe tener ID tras commit"

    payload = {"precio_base": 200.00}
    response = admin_client.patch(f"/api/servicios/{servicio.id}", json=payload)

    if response.status_code != 200:
        print(f"DEBUG: Error actualizar servicio: {response.json()}")
    assert response.status_code == 200
    assert Decimal(str(response.json()["precio_base"])) == Decimal("200.00")
