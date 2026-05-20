"""Helper centralizado de zona horaria para TEAMSA.

Evita depender de la hora del servidor (que puede estar en UTC).
Todas las comparaciones de 'hoy' y 'ahora' deben usar estos helpers.
"""
from datetime import datetime, date, timezone, timedelta

# Zona horaria de Ciudad de México (UTC-6, sin horario de verano desde 2023)
ZONA_MEXICO = timezone(timedelta(hours=-6))


def ahora_mexico() -> datetime:
    """Retorna datetime actual en zona horaria de México."""
    return datetime.now(ZONA_MEXICO)


def hoy_mexico() -> date:
    """Retorna la fecha actual en zona horaria de México."""
    return ahora_mexico().date()


def calcular_estado_temporal(
    fecha_inicio: date,
    fecha_fin: date,
    estados_activos: list[str],
    estado_actual: str
) -> str:
    """Calcula estado visual basado en rango de fechas vs hoy."""
    if estado_actual not in estados_activos:
        return estado_actual
    hoy = hoy_mexico()
    if hoy < fecha_inicio:
        return "programado"
    elif fecha_inicio <= hoy <= fecha_fin:
        return "en_curso"
    elif hoy > fecha_fin:
        return "fase_final"
    return estado_actual
