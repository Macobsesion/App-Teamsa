"""
Estrategias para generación de folios (Strategy Pattern).
"""
from typing import Protocol
from datetime import date

class GeneradorFolio(Protocol):
    """Protocolo que define cómo se debe comportar una estrategia de generación de folio."""
    
    def generar(self, prefijo: str, id_entidad: int, fecha: date) -> str:
        ...

class EstrategiaFolioFechaId:
    """
    Estrategia estándar: PREFIJO-YYMMDD-ID
    Ejemplo: OT-250129-45
    """
    def generar(self, prefijo: str, id_entidad: int, fecha: date) -> str:
        fecha_str = fecha.strftime("%y%m%d")
        return f"{prefijo}-{fecha_str}-{id_entidad}"

class EstrategiaFolioSimple:
    """
    Estrategia simple: PREFIJO-0000 ID
    Ejemplo: OT-00045 (relleno con ceros)
    """
    def __init__(self, ceros: int = 5):
        self.ceros = ceros

    def generar(self, prefijo: str, id_entidad: int, fecha: date) -> str:
        return f"{prefijo}-{str(id_entidad).zfill(self.ceros)}"

class GeneradorFoliosHelper:
    """Helper simple para simular un generador de secuencias sin estado (para MVP)."""
    def siguiente_folio(self, prefijo: str) -> str:
        from datetime import datetime
        import random
        # Generación aleatoria para evitar colisiones en MVP sin secuencia DB real
        suffix = random.randint(1000, 9999)
        return f"{prefijo}-{datetime.now().strftime('%Y%m%d')}-{suffix}"

# Instancia global
generador_folios = GeneradorFoliosHelper()
