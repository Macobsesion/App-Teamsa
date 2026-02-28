from decimal import Decimal
import pytest
from app.modulos.cotizaciones.calculadora import ServicioCalculadoraCotizacion

class MockItem:
    def __init__(self, cantidad, precio, descuento=0):
        self.cantidad = Decimal(str(cantidad))
        self.precio_unitario = Decimal(str(precio))
        self.descuento_porcentaje = Decimal(str(descuento))

def test_calculo_simple_sin_iva():
    """Prueba un solo item sin descuento."""
    items = [MockItem(10, 100)] # 1000
    
    totales = ServicioCalculadoraCotizacion.calcular_totales(items)
    
    assert totales["subtotal"] == Decimal("1000.00")
    assert totales["descuento_global"] == Decimal("0.00")
    assert totales["iva"] == Decimal("160.00") # 16% de 1000
    assert totales["total"] == Decimal("1160.00")

def test_calculo_con_descuento():
    """Prueba item con 10% de descuento."""
    items = [MockItem(10, 100, 10)] # Sub: 1000, Desc: 100, Base: 900
    
    totales = ServicioCalculadoraCotizacion.calcular_totales(items)
    
    assert totales["subtotal"] == Decimal("1000.00")
    assert totales["descuento_global"] == Decimal("100.00")
    assert totales["iva"] == Decimal("144.00") # 16% de 900
    assert totales["total"] == Decimal("1044.00") # 900 + 144

def test_multiples_items():
    """Prueba múltiples items mezclados."""
    items = [
        MockItem(1, 100, 0),   # 100, Base 100
        MockItem(2, 50, 20),   # 100, Desc 20, Base 80
    ]
    # Subtotal: 200
    # Descuento: 20
    # Base: 180
    # IVA: 28.8
    # Total: 208.8
    
    totales = ServicioCalculadoraCotizacion.calcular_totales(items)
    
    assert totales["subtotal"] == Decimal("200.00")
    assert totales["descuento_global"] == Decimal("20.00")
    assert totales["iva"] == Decimal("28.80")
    assert totales["total"] == Decimal("208.80")
