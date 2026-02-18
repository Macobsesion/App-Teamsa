import pytest
import uuid
from app.modulos.proveedores.proveedores_modelo import Proveedor
from tests.factories import ProveedorFactory


def test_crear_proveedor(admin_client, session):
    """Prueba creación de proveedor."""
    unique_name = f"Proveedor Test {uuid.uuid4()}"
    payload = {
        "nombre": unique_name,
        "rfc": "PROV010101000",
        "razon_social": "Proveedor Test S.A.",
        "activo": True
    }
    response = admin_client.post("/api/proveedores", json=payload)
    if response.status_code != 200:
        print(f"DEBUG PROV: {response.json()}")
    assert response.status_code == 200
    assert response.json()["rfc"] == "PROV010101000"


def test_listar_proveedores(admin_client, session):
    """Prueba listado."""
    for _ in range(2):
        p = ProveedorFactory()
        session.add(p)
    session.commit()

    response = admin_client.get("/api/proveedores")
    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_buscar_proveedor(admin_client, session):
    """Prueba búsqueda por nombre (campo_busqueda=nombre)."""
    unique = str(uuid.uuid4())[:8]
    nombre_unico = f"ProvBusqueda {unique}"
    p1 = ProveedorFactory(nombre=nombre_unico)
    session.add(p1)
    p2 = ProveedorFactory(nombre=f"OtroProveedor {uuid.uuid4()}")
    session.add(p2)
    session.commit()

    response = admin_client.get(f"/api/proveedores?q={nombre_unico}")
    data = response.json()
    assert len(data) >= 1
    assert any(p["nombre"] == nombre_unico for p in data)
