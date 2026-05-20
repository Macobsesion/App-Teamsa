import pytest
from datetime import date
from app.base.eventos import BusEventos
from app.base.folios import EstrategiaFolioFechaId

def test_bus_eventos_pub_sub():
    """Verifica que el bus de eventos publique y suscriba correctamente."""
    resultados = []
    
    def handler_test(payload):
        resultados.append(payload)
        
    BusEventos.limpiar()
    BusEventos.suscribir("test_event", handler_test)
    
    BusEventos.publicar("test_event", "Hola Mundo")
    
    assert len(resultados) == 1
    assert resultados[0] == "Hola Mundo"

def test_estrategia_folio_fecha_id():
    """Verifica la estrategia estándar de folios."""
    estrategia = EstrategiaFolioFechaId()
    fecha = date(2025, 1, 30)
    folio = estrategia.generar("TEST", 123, fecha)
    
    # Formato esperado: TEST-YYMMDD-ID => TEST-250130-123
    assert folio == "TEST-250130-123"

