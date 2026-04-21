"""
Utilidades Jinja (filtros + plantilla compartida).

- fmt_dt: formatea datetime/date a "YYYY-MM-DD HH:MM" (o solo fecha si no hay hora)
- fmt_time: formatea time a "HH:MM"
- fmt_none: muestra cadena vacía si el valor es None

Incluye helper `register_jinja_filters(templates)` para registrar filtros
en una instancia de Jinja2Templates y `get_templates()` para obtener una
instancia compartida con los filtros ya registrados (evita repetir boilerplate).
"""
from __future__ import annotations

from datetime import date, datetime, time
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates  # type: ignore


def fmt_dt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)


def fmt_time(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value)


def fmt_none(value: Any, fallback: str = "") -> str:
    """Evita la visualización de None o el string literal 'None'."""
    if value is None:
        return fallback
    str_val = str(value).strip().lower()
    if not str_val or str_val in ("none", "null", "undefined"):
        return fallback
    return str(value)


def fmt_fecha_es(value: Any) -> str:
    """Formatea una fecha en español (ej: '5 de diciembre de 2025')."""
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        # Importación lazy para evitar dependencias circulares
        from app.base.utilidades_fecha import formatear_fecha_español
        # Convertir datetime a date si es necesario
        fecha = value.date() if isinstance(value, datetime) else value
        return formatear_fecha_español(fecha)
    return str(value)



def register_jinja_filters(templates: Jinja2Templates) -> None:
    env = templates.env
    env.filters["fmt_dt"] = fmt_dt
    env.filters["fmt_time"] = fmt_time
    env.filters["fmt_none"] = fmt_none
    env.filters["fmt_fecha_es"] = fmt_fecha_es

    def fmt_date(value: Any, format: str = "%d/%m/%Y") -> str:
        """Formatea fecha/datetime de forma segura. Si es None, devuelve '-'."""
        if value is None:
            return "-"
        if isinstance(value, (datetime, date)):
            return value.strftime(format)
        return str(value)
    env.filters["fmt_date"] = fmt_date
    
    def fmt_currency(value: Any) -> str:
        if value is None:
            return "0.00"
        try:
            # Saneamiento previo si es string basura
            if isinstance(value, str) and value.strip().lower() in ("none", "null"):
                return "0.00"
            return "{:,.2f}".format(float(value))
        except (ValueError, TypeError):
            return str(value)
    env.filters["fmt_currency"] = fmt_currency
    # Helper global para obtener atributos o claves dinámicamente desde plantillas
    def getv(obj, name, default=""):
        try:
            if obj is None:
                return default
            if hasattr(obj, "get"):
                val = obj.get(name, getattr(obj, name, default))
            else:
                val = getattr(obj, name, default)
            
            # Filtro agresivo contra basura 'none' o nulos
            if val is None:
                return default
            if isinstance(val, str) and (not val.strip() or val.strip().lower() in ("none", "null", "undefined")):
                return default
                
            return val
        except Exception:
            return default
    env.globals["getv"] = getv
    env.globals["now"] = datetime.now


@lru_cache
def get_templates() -> Jinja2Templates:
    """Devuelve una instancia única de Jinja2Templates con filtros registrados."""
    root = Path(__file__).resolve().parents[2]
    templates_dir = root / "web" / "templates"
    tpl = Jinja2Templates(directory=str(templates_dir))
    register_jinja_filters(tpl)
    return tpl
