import pytest
from app.modulos.cotizaciones.calculadora import ServicioCalculadoraCotizacion

@pytest.mark.parametrize("letras, esperado", [
    ([], "B"),
    ([None], "B"),
    (["B"], "C"),
    (["C"], "D"),
    (["Z"], "AA"),
    (["AA"], "AB"),
    (["AZ"], "BA"),
    (["ZZ"], "AAA"),
    (["A", "C", "B"], "D"), # Debe tomar el max
])
def test_calcular_siguiente_letra(letras, esperado):
    assert ServicioCalculadoraCotizacion.calcular_siguiente_letra(letras) == esperado

@pytest.mark.parametrize("numero, esperado", [
    ("COT-001", "COT-001"),
    ("COT-001-B", "COT-001"),
    ("COT-001-C", "COT-001"),
    ("COT-YYMMDD-123", "COT-YYMMDD-123"),
    ("COT-YYMMDD-123-B", "COT-YYMMDD-123"), # Caso nuevo
    ("TEMP-PENDING", "TEMP-PENDING"),
])
def test_extraer_numero_base(numero, esperado):
    assert ServicioCalculadoraCotizacion.extraer_numero_base(numero) == esperado
