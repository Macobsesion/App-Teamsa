"""Utilidades para manejo de fechas en español."""
from datetime import date

MESES_ESPAÑOL = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}


def formatear_fecha_español(fecha: date) -> str:
    """
    Formatea una fecha en español.
    
    Args:
        fecha: Fecha a formatear
        
    Returns:
        String con formato "5 de diciembre de 2025"
        
    Example:
        >>> fecha = date(2025, 12, 5)
        >>> formatear_fecha_español(fecha)
        '5 de diciembre de 2025'
    """
    return f"{fecha.day} de {MESES_ESPAÑOL[fecha.month]} de {fecha.year}"
