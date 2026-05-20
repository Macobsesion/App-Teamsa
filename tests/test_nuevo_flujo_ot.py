"""
Tests para el nuevo flujo de Órdenes de Trabajo:
- Empalme de horario de técnico
- Concepto ya asignado a otra OT
- Completar concepto (irreversible)
- Crear OT desde cotización con conceptos y técnico
"""
import pytest
from decimal import Decimal
from datetime import date, datetime
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo, ConceptoOrdenTrabajo
from app.modulos.ordenes_trabajo.enums import EstadoConceptoOT
from app.modulos.ordenes_trabajo.ordenes_trabajo_repositorio import RepositorioOrden
from app.modulos.ordenes_trabajo.ordenes_trabajo_servicios import (
    ServicioOrdenes, EmpalmeError, ConceptoYaAsignadoError, ConceptoCompletadoError
)
from app.modulos.cotizaciones.enums import EstadoCotizacion
from app.modulos.usuarios.usuarios_modelo import Usuario
from tests.factories import (
    CotizacionFactory, ConceptoCotizacionFactory, ClienteFactory, OrdenTrabajoFactory
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def cotizacion_base(session):
    """Cotización con dos conceptos libres, lista para crear OT."""
    cliente = ClienteFactory(nombre="Test Corp", direccion="Av. 100", contacto="José")
    session.add(cliente)
    session.flush()

    cot = CotizacionFactory(
        estado=EstadoCotizacion.ENVIADA.value,
        cliente=cliente,
        cliente_id=cliente.id,
        folio="COT-FLUJO-OT",
    )
    session.add(cot)
    session.flush()

    c1 = ConceptoCotizacionFactory(
        cotizacion=cot, cotizacion_id=cot.id,
        descripcion="Servicio A", importe=Decimal("500.00"),
    )
    c2 = ConceptoCotizacionFactory(
        cotizacion=cot, cotizacion_id=cot.id,
        descripcion="Servicio B", importe=Decimal("300.00"),
    )
    session.add_all([c1, c2])
    session.commit()
    return cot


@pytest.fixture
def tecnico(session):
    """Usuario con rol 'tecnico' para pruebas de asignación."""
    t = Usuario(
        usuario="tec_test",
        nombres="Técnico Test",
        email="tec@test.com",
        rol="tecnico",
        hashed_password="dummy",
        activo=True,
        creado_por="TEST",
        modificado_por="TEST",
    )
    session.add(t)
    session.commit()
    return t


@pytest.fixture
def servicio(session):
    from app.base.folios import EstrategiaFolioFechaId
    return ServicioOrdenes(session, EstrategiaFolioFechaId())


# ─── Test: crear OT con conceptos seleccionados ───────────────────────────────

def test_crear_ot_con_conceptos_seleccionados(session, cotizacion_base, servicio, admin_client):
    """
    Verifica que al crear una OT con concepto_ids, se guarden snapshots
    de los conceptos seleccionados.
    """
    concepto_ids = [c.id for c in cotizacion_base.conceptos]
    assert len(concepto_ids) == 2

    payload = {
        "cotizacion_id": cotizacion_base.id,
        "fecha_programada": str(date.today()),
        "hora_programada": "10:00",
        "duracion": 2,
        "concepto_ids": concepto_ids,
    }

    resp = admin_client.post("/api/ordenes-trabajo/crear-desde-cotizacion", json=payload)
    assert resp.status_code in (200, 201), resp.json()

    data = resp.json()
    assert data["cotizacion_id"] == cotizacion_base.id
    assert len(data["conceptos"]) == 2

    # Los conceptos deben estar en estado pendiente
    for c in data["conceptos"]:
        assert c["estado"] == "pendiente"


# ─── Test: crear OT con técnico ──────────────────────────────────────────────

def test_crear_ot_con_tecnico(session, cotizacion_base, tecnico, admin_client):
    """
    Verifica que se puede crear una OT asignando un técnico con rol correcto.
    """
    payload = {
        "cotizacion_id": cotizacion_base.id,
        "fecha_programada": str(date.today()),
        "hora_programada": "08:00",
        "duracion": 2,
        "concepto_ids": [],
        "tecnico_id": tecnico.id,
    }

    resp = admin_client.post("/api/ordenes-trabajo/crear-desde-cotizacion", json=payload)
    assert resp.status_code in (200, 201), resp.json()

    data = resp.json()
    assert data["tecnico_id"] == tecnico.id
    assert data["tecnico_nombre"] == tecnico.nombres


# ─── Test: empalme de técnico ────────────────────────────────────────────────

def test_empalme_tecnico_mismo_horario(session, cotizacion_base, tecnico, servicio):
    """
    Verifica que no se puede asignar un técnico que ya tiene otra OT
    en el mismo horario (empalme).
    """
    # Crear primera OT con el técnico
    ot1 = OrdenTrabajoFactory(
        cotizacion_id=cotizacion_base.id,
        cliente_nombre="Cliente A",
        domicilio="Dir A",
        contacto="Contacto A",
        fecha_programada=date.today(),
        hora_programada="10:00",
        duracion=3,          # 10:00 – 13:00
        tecnico_id=tecnico.id,
        tecnico_nombre=tecnico.nombres,
    )
    session.add(ot1)
    session.commit()

    # Intentar asignar el mismo técnico en horario solapado (11:00 – 12:00)
    conflicto = servicio.verificar_empalme_tecnico(
        tecnico_id=tecnico.id,
        fecha=date.today(),
        hora="11:00",
        duracion=1,
    )
    assert conflicto is not None, "Debería detectar empalme"


def test_sin_empalme_tecnico_horario_diferente(session, cotizacion_base, tecnico, servicio):
    """
    Verifica que NO hay empalme si la OT está en horario distinto (después).
    """
    ot1 = OrdenTrabajoFactory(
        cotizacion_id=cotizacion_base.id,
        cliente_nombre="Cliente B",
        domicilio="Dir B",
        contacto="Contacto B",
        fecha_programada=date.today(),
        hora_programada="08:00",
        duracion=2,          # 08:00 – 10:00
        tecnico_id=tecnico.id,
        tecnico_nombre=tecnico.nombres,
    )
    session.add(ot1)
    session.commit()

    # 10:30 no se empalma con 08:00-10:00
    conflicto = servicio.verificar_empalme_tecnico(
        tecnico_id=tecnico.id,
        fecha=date.today(),
        hora="10:30",
        duracion=2,
    )
    assert conflicto is None, "No debería haber empalme en horario diferente"


def test_empalme_via_endpoint_retorna_409(session, cotizacion_base, tecnico, admin_client):
    """
    Verifica que el endpoint devuelve 409 si hay empalme de técnico.
    """
    # Crear primera OT que ocupa 09:00-11:00
    ot1 = OrdenTrabajoFactory(
        cotizacion_id=cotizacion_base.id,
        cliente_nombre="Cliente C",
        domicilio="Dir C",
        contacto="Contacto C",
        fecha_programada=date.today(),
        hora_programada="09:00",
        duracion=2,
        tecnico_id=tecnico.id,
        tecnico_nombre=tecnico.nombres,
    )
    session.add(ot1)
    session.commit()

    # Intentar crear segunda OT solapada (10:00)
    payload = {
        "cotizacion_id": cotizacion_base.id,
        "fecha_programada": str(date.today()),
        "hora_programada": "10:00",
        "duracion": 2,
        "concepto_ids": [],
        "tecnico_id": tecnico.id,
    }
    resp = admin_client.post("/api/ordenes-trabajo/crear-desde-cotizacion", json=payload)
    assert resp.status_code == 409, resp.json()
    assert "empalme" in resp.json()["detail"].lower() or "ot" in resp.json()["detail"].lower()


# ─── Test: concepto ya asignado a otra OT ────────────────────────────────────

def test_concepto_ya_asignado_retorna_409(session, cotizacion_base, admin_client):
    """
    Verifica que no se puede incluir el mismo concepto en dos OTs distintas.
    """
    from datetime import timedelta

    concepto = cotizacion_base.conceptos[0]
    payload_base = {
        "cotizacion_id": cotizacion_base.id,
        "fecha_programada": str(date.today()),
        "hora_programada": "14:00",
        "duracion": 1,
        "concepto_ids": [concepto.id],
    }

    # Primera OT — OK
    resp1 = admin_client.post("/api/ordenes-trabajo/crear-desde-cotizacion", json=payload_base)
    assert resp1.status_code in (200, 201), resp1.json()

    # Segunda OT con el mismo concepto — diferente día para evitar colisión de folio
    # (el folio incluye la fecha, pero el ID de la BD garantiza unicidad real)
    # El error debe ser ConceptoYaAsignadoError → 409, antes del INSERT de la OT
    payload2 = {
        **payload_base,
        "hora_programada": "16:00",
        "fecha_programada": str(date.today() + timedelta(days=1)),
    }
    resp2 = admin_client.post("/api/ordenes-trabajo/crear-desde-cotizacion", json=payload2)
    assert resp2.status_code == 409, resp2.json()


# ─── Test: completar concepto (irreversible) ─────────────────────────────────

def test_completar_concepto_irreversible(session, cotizacion_base, admin_client):
    """
    Verifica que:
    1. Se puede marcar un concepto como 'completado'.
    2. No se puede volver a completar (409).
    """
    concepto = cotizacion_base.conceptos[0]

    # Crear OT con ese concepto
    payload = {
        "cotizacion_id": cotizacion_base.id,
        "fecha_programada": str(date.today()),
        "hora_programada": "07:00",
        "duracion": 1,
        "concepto_ids": [concepto.id],
    }
    resp = admin_client.post("/api/ordenes-trabajo/crear-desde-cotizacion", json=payload)
    assert resp.status_code in (200, 201), resp.json()

    ot_id = resp.json()["id"]
    concepto_ot_id = resp.json()["conceptos"][0]["id"]

    # Completar
    resp_completar = admin_client.post(
        f"/api/ordenes-trabajo/{ot_id}/conceptos/{concepto_ot_id}/completar"
    )
    assert resp_completar.status_code == 200, resp_completar.json()
    data = resp_completar.json()
    assert data["estado"] == "completado"
    assert data["completado_por"] is not None

    # Intentar completar de nuevo — debe ser 409
    resp_doble = admin_client.post(
        f"/api/ordenes-trabajo/{ot_id}/conceptos/{concepto_ot_id}/completar"
    )
    assert resp_doble.status_code == 409, resp_doble.json()


def test_completar_concepto_registra_usuario(session, cotizacion_base, admin_client):
    """
    Verifica que el campo 'completado_por' se registra con el usuario que hizo la acción.
    """
    concepto = cotizacion_base.conceptos[1]

    payload = {
        "cotizacion_id": cotizacion_base.id,
        "fecha_programada": str(date.today()),
        "hora_programada": "06:00",
        "duracion": 1,
        "concepto_ids": [concepto.id],
    }
    resp = admin_client.post("/api/ordenes-trabajo/crear-desde-cotizacion", json=payload)
    assert resp.status_code in (200, 201)

    ot_id = resp.json()["id"]
    c_ot_id = resp.json()["conceptos"][0]["id"]

    resp_c = admin_client.post(f"/api/ordenes-trabajo/{ot_id}/conceptos/{c_ot_id}/completar")
    assert resp_c.status_code == 200
    assert resp_c.json()["completado_por"] is not None
    assert resp_c.json()["fecha_completado"] is not None


# ─── Test: Finalización y Cancelación (Eventos de Dominio) ───────────────────

def test_auto_finalizar_ot_al_completar_todos_conceptos(session, cotizacion_base, admin_client):
    """
    Verifica que cuando el último concepto de una OT se completa:
    1. La OT cambia su estado a 'finalizada' automáticamente.
    2. La Cotización asociada cambia su estado a 'finalizada'.
    """
    # Crear OT con los 2 conceptos de la cotización
    concepto_ids = [c.id for c in cotizacion_base.conceptos]
    payload = {
        "cotizacion_id": cotizacion_base.id,
        "fecha_programada": str(date.today()),
        "hora_programada": "08:00",
        "duracion": 2,
        "concepto_ids": concepto_ids,
    }
    resp = admin_client.post("/api/ordenes-trabajo/crear-desde-cotizacion", json=payload)
    assert resp.status_code in (200, 201)
    
    ot_data = resp.json()
    ot_id = ot_data["id"]
    c1_id = ot_data["conceptos"][0]["id"]
    c2_id = ot_data["conceptos"][1]["id"]
    
    # La OT recién creada debe estar 'programada' (o 'en_curso') y no finalizada
    assert ot_data["estado"] != "finalizada"
    
    # La Cotización debió pasar a 'programada' por el evento de creación
    # Nota: la sesión usada por pytest puede necesitar expirar para ver cambios externos
    # No la revisaremos aquí (se prueba en otro lado o confiaremos en el evento final)
    
    # Completar primer concepto
    resp_c1 = admin_client.post(f"/api/ordenes-trabajo/{ot_id}/conceptos/{c1_id}/completar")
    assert resp_c1.status_code == 200
    
    # Verificar que la OT sigue sin estar finalizada (falta el c2)
    resp_ot_1 = admin_client.get(f"/api/ordenes-trabajo/{ot_id}")
    assert resp_ot_1.json()["estado"] != "finalizada"
    
    # Completar segundo concepto
    resp_c2 = admin_client.post(f"/api/ordenes-trabajo/{ot_id}/conceptos/{c2_id}/completar")
    assert resp_c2.status_code == 200
    
    # Ahora la OT debe estar finalizada
    resp_ot_2 = admin_client.get(f"/api/ordenes-trabajo/{ot_id}")
    assert resp_ot_2.json()["estado"] == "finalizada"
    
    # Y la cotización también (vía evento EVENTO_ORDEN_FINALIZADA)
    resp_cot = admin_client.get(f"/api/cotizaciones/{cotizacion_base.id}")
    assert resp_cot.json()["estado"] == "finalizada"


def test_cancelar_ot_y_revertir_cotizacion(session, cotizacion_base, admin_client):
    """
    Verifica que al cancelar una OT:
    1. La OT queda en 'cancelada'.
    2. Si era la única OT de la cotización, la cotización regresa a 'enviada'.
    """
    # Crear OT 
    payload = {
        "cotizacion_id": cotizacion_base.id,
        "fecha_programada": str(date.today()),
        "hora_programada": "10:00",
        "duracion": 1,
        "concepto_ids": [],
    }
    resp = admin_client.post("/api/ordenes-trabajo/crear-desde-cotizacion", json=payload)
    assert resp.status_code in (200, 201)
    ot_id = resp.json()["id"]
    
    # Cancelar la OT
    resp_cancelar = admin_client.post(f"/api/ordenes-trabajo/{ot_id}/cancelar")
    assert resp_cancelar.status_code == 200
    assert resp_cancelar.json()["estado"] == "cancelada"
    
    # Validar que la cotización regresó a enviada
    resp_cot = admin_client.get(f"/api/cotizaciones/{cotizacion_base.id}")
    assert resp_cot.json()["estado"] in ("enviada", "aceptada")

