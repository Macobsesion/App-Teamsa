"""
Estrategias para generación de folios (Strategy Pattern).
"""
from typing import Protocol
from datetime import date

class GeneradorFolio(Protocol):
    """Protocolo que define cómo se debe comportar una estrategia de generación de folio."""
    
    def generar(self, prefijo: str, id_entidad: int, fecha: date) -> str:
        ...

class EstrategiaFolioMensual:
    """
    Estrategia de reinicio mensual: PREFIJO-YYMMNN
    Ejemplo: COT-250101, COT-250102...
    """
    def __init__(self, digitos_secuencia: int = 2):
        self.digitos_secuencia = digitos_secuencia

    def generar(self, prefijo: str, fecha: date, secuencia: int) -> str:
        fecha_str = fecha.strftime("%y%m")
        sec_str = str(secuencia).zfill(self.digitos_secuencia)
        return f"{prefijo}-{fecha_str}{sec_str}"

class EstrategiaFolioHeredado:
    """
    Estrategia heredada: PREFIJO-BASE-X
    Ejemplo: VIA-250101-1, OT-250101-2
    """
    def generar(self, prefijo: str, base: str, secuencia: int) -> str:
        # base ya tiene el formato YYMMNN (sin el prefijo del padre)
        return f"{prefijo}-{base}-{secuencia}"

class EstrategiaFolioFechaId:
    """
    Estrategia legacy: PREFIJO-AAMMDD-ID
    Mantenida por compatibilidad con módulos no migrados.
    """
    def generar(self, prefijo: str, id_entidad: int, fecha: date) -> str:
        fecha_str = fecha.strftime("%y%m%d")
        return f"{prefijo}-{fecha_str}-{id_entidad}"

class EstrategiaFolioSimple:
    """
    Estrategia simple: PREFIJO-ID (con padding de ceros)
    Mantenida por compatibilidad con tests y casos básicos.
    """
    def __init__(self, ceros: int = 4):
        self.ceros = ceros

    def generar(self, prefijo: str, id_entidad: int, fecha: date = None) -> str:
        con_ceros = str(id_entidad).zfill(self.ceros)
        return f"{prefijo}-{con_ceros}"
