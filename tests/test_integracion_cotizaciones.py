"""
Tests de integración para Cotizaciones usando la nueva infraestructura.
"""
import pytest
from decimal import Decimal
from sqlmodel import select

from app.modulos.clientes.clientes_modelo import Cliente
from app.modulos.cotizaciones.cotizaciones_servicios import ServicioCreacionCotizacion
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from tests.factories import ClienteFactory, ServicioFactory

# No necesitamos importar sesión o engine, se inyectan automáticamente por conftest via 'session' fixture

def test_creacion_cotizacion_completa(session):
    """
    Verifica que se puede crear una cotización completa usando el servicio.
    Usa Factories para crear datos previos (Cliente).
    """
    # 1. Preparar datos usando Factories
    cliente = ClienteFactory()
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    
    # 2. Ejecutar el servicio (SUT - System Under Test)
    servicio = ServicioCreacionCotizacion(session)
    
    datos_entrada = {
        "cliente_id": cliente.id,
        "metodo_pago": "PUE",
        "forma_pago": "03",
        "notas": "Test Integration",
        "usuario_id": "TEST_BOT",
        "servicios": [
            {
                "servicio_id": None,
                "codigo_sat": "81111111",
                "descripcion": "Servicio de Prueba",
                "unidad": "H87",
                "cantidad": 2,
                "precio_unitario": 100.00,
                "descuento_porcentaje": 0
            }
        ]
    }
    
    cotizacion = servicio.crear_documento(datos_entrada, datos_entrada['servicios'])
    
    # 3. Assertions
    assert cotizacion.id is not None
    assert cotizacion.numero.startswith("COT-")
    assert cotizacion.cliente_id == cliente.id
    
    # Verificar cálculos
    # 2 * 100 = 200 subtotal
    assert cotizacion.subtotal == Decimal("200.00")
    # IVA 16% = 32
    assert cotizacion.iva == Decimal("32.00")
    assert cotizacion.total == Decimal("232.00")
    
    # Verificar persistencia
    cotizacion_db = session.get(Cotizacion, cotizacion.id)
    assert cotizacion_db is not None
    assert len(cotizacion_db.conceptos) == 1
    assert cotizacion_db.conceptos[0].descripcion == "Servicio de Prueba"

def test_aislamiento_de_datos(session):
    """
    Verifica que la base de datos está limpia (o al menos aislada de otros tests).
    Si los fixtures funcionan, este test no debería ver datos creados en el test anterior.
    """
    # Contar cotizaciones creadas por "TEST_BOT"
    # Ojo: Si la BD tenía datos de antes, los verá. 
    # Pero no debería ver la del test_creacion_cotizacion_completa si corrió antes y hubo rollback.
    statement = select(Cotizacion).where(Cotizacion.notas == "Test Integration")
    resultados = session.exec(statement).all()
    
    # Debería ser 0 porque el test anterior hizo rollback al final de su ejecución
    assert len(resultados) == 0
