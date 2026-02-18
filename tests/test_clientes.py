import pytest
import uuid
from app.modulos.clientes.clientes_modelo import Cliente
from tests.factories import ClienteFactory


def test_crear_cliente_exitoso(admin_client, session):
    """Verifica que se puede crear un cliente correctamente."""
    unique = str(uuid.uuid4())[:8]
    payload = {
        "nombre": f"Cliente Test {unique}",
        "rfc": "XAXX010101000",
        "razon_social": "Cliente Test S.A. de C.V.",
        "email": "contacto@cliente.com",
        "direccion": "Calle Falsa 123",
        "ciudad": "Ciudad de Prueba",
        "cp": "12345",
        "telefono": "5551234567",
        "contacto": "Juan Pérez",
        "activo": True
    }

    response = admin_client.post("/api/clientes", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["nombre"] == payload["nombre"]
    assert data["rfc"] == payload["rfc"]
    assert data["id"] is not None


def test_leer_clientes(admin_client, session):
    """Verifica el listado de clientes."""
    for _ in range(3):
        c = ClienteFactory()
        session.add(c)
    session.commit()

    response = admin_client.get("/api/clientes")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3


def test_actualizar_cliente(admin_client, session):
    """Verifica actualización de un cliente."""
    cliente = ClienteFactory()
    session.add(cliente)
    session.flush()
    session.commit()

    assert cliente.id is not None, "El cliente debe tener ID tras commit"

    payload = {"nombre": "Nombre Actualizado"}
    response = admin_client.patch(f"/api/clientes/{cliente.id}", json=payload)

    if response.status_code != 200:
        print(f"DEBUG UPDATE: {response.status_code} - {response.json()}")
    assert response.status_code == 200
    assert response.json()["nombre"] == "Nombre Actualizado"


def test_buscar_cliente(admin_client, session):
    """Verifica la búsqueda de clientes por nombre (campo_busqueda=nombre)."""
    unique = str(uuid.uuid4())[:8]
    nombre_unico = f"BusquedaCliente {unique}"
    cliente = ClienteFactory(nombre=nombre_unico)
    session.add(cliente)
    session.commit()

    response = admin_client.get(f"/api/clientes?q={nombre_unico}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(c["nombre"] == nombre_unico for c in data)


def test_eliminar_cliente(admin_client, session):
    """Verifica eliminación."""
    cliente = ClienteFactory()
    session.add(cliente)
    session.flush()
    session.commit()

    assert cliente.id is not None

    response = admin_client.delete(f"/api/clientes/{cliente.id}")
    # El endpoint CRUD genérico devuelve 204 No Content
    assert response.status_code == 204
