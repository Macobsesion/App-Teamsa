"""Tests de integración para el módulo de Órdenes de Compra."""
from decimal import Decimal
from datetime import date
from sqlmodel import select

from app.modulos.ordenes_compra.ordenes_compra_servicios import ServicioCreacionOrdenCompra
from tests.factories import ProveedorFactory, ServicioProveedorFactory

def test_creacion_completa_orden_compra(session):
    """Verifica el flujo completo de creación de una orden de compra."""
    # 1. Setup Data
    proveedor = ProveedorFactory()
    session.add(proveedor)
    session.commit()
    session.refresh(proveedor)
    
    servicio_prov = ServicioProveedorFactory(proveedor_id=proveedor.id, costo_unitario=Decimal("100.00"))
    session.add(servicio_prov)
    session.commit()
    session.refresh(servicio_prov)
    
    # 2. Ejecutar Servicio
    servicio_dominio = ServicioCreacionOrdenCompra(session)
    
    datos = {
        "proveedor_id": proveedor.id,
        "fecha_emision": date.today(),
        "notas": "Pedido Urgente",
        "usuario_id": "TEST_BUYER",
        "detalles": [
            {
                "servicio_proveedor_id": servicio_prov.id,
                "codigo_sku": servicio_prov.codigo_sku,
                "descripcion": servicio_prov.descripcion,
                "unidad": "Caja",
                "cantidad": 5, # 5 * 100 = 500
                "precio_unitario": 100.00
            }
        ]
    }
    
    orden = servicio_dominio.crear_documento(datos, datos['detalles'])
    
    # 3. Assertions
    assert orden.id is not None
    assert orden.folio.startswith("OC")
    assert orden.proveedor_id == proveedor.id
    
    # Verificar Totales (Mixin Financiero)
    # Subtotal: 500.00
    # IVA 16%: 80.00
    # Total: 580.00
    assert orden.subtotal == Decimal("500.00")
    assert orden.iva == Decimal("80.00")
    assert orden.total == Decimal("580.00")
    
    # Verificar Persistencia Detalles
    assert len(orden.detalles) == 1
    det = orden.detalles[0]
    assert det.cantidad == Decimal("5.00")
    assert det.importe == Decimal("500.00")
