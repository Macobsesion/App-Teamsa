"""Tests de integración para el módulo de Servicios de Proveedor."""
import uuid
from decimal import Decimal
from sqlmodel import select

from app.modulos.servicios_proveedores.servicios_proveedores_modelo import ServicioProveedor
from tests.factories import ProveedorFactory, ServicioProveedorFactory


def test_crear_servicio_proveedor(session):
    """Verifica que se puede crear un servicio asociado a un proveedor."""
    # 1. Crear Proveedor
    proveedor = ProveedorFactory()
    session.add(proveedor)
    session.flush()
    session.commit()
    session.refresh(proveedor)

    # 2. Crear Servicio manualmente (evitar SubFactory que crea su propio proveedor)
    unique_sku = f"SKU-{uuid.uuid4().hex[:8]}"
    servicio = ServicioProveedor(
        proveedor_id=proveedor.id,
        codigo_sku=unique_sku,
        descripcion="Tuercas Test",
        costo_unitario=Decimal("50.00"),
        moneda="MXN",
        creado_por="TEST_FACTORY",
        modificado_por="TEST_FACTORY"
    )
    session.add(servicio)
    session.commit()
    session.refresh(servicio)

    assert servicio.id is not None
    assert servicio.proveedor_id == proveedor.id
    assert servicio.costo_unitario == Decimal("50.00")

    # 3. Verificar relación inversa
    session.refresh(proveedor)
    assert len(proveedor.servicios) >= 1
    assert any(s.id == servicio.id for s in proveedor.servicios)


def test_busqueda_servicios(session):
    """Test de búsqueda básica con nombres únicos para evitar colisiones."""
    proveedor = ProveedorFactory()
    session.add(proveedor)
    session.flush()
    session.commit()

    unique_tag = uuid.uuid4().hex[:8]
    s1 = ServicioProveedor(
        proveedor_id=proveedor.id,
        descripcion=f"Tuercas {unique_tag}",
        codigo_sku=f"A1-{unique_tag}",
        costo_unitario=Decimal("25.00"),
        moneda="MXN",
        creado_por="TEST_FACTORY",
        modificado_por="TEST_FACTORY"
    )
    s2 = ServicioProveedor(
        proveedor_id=proveedor.id,
        descripcion=f"Tornillos {unique_tag}",
        codigo_sku=f"A2-{unique_tag}",
        costo_unitario=Decimal("30.00"),
        moneda="MXN",
        creado_por="TEST_FACTORY",
        modificado_por="TEST_FACTORY"
    )

    session.add(s1)
    session.add(s2)
    session.commit()

    stmt = select(ServicioProveedor).where(
        ServicioProveedor.descripcion.contains(f"Tuercas {unique_tag}")
    )
    res = session.exec(stmt).all()

    assert len(res) == 1
    assert res[0].codigo_sku == f"A1-{unique_tag}"
