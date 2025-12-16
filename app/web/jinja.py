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
    return fallback if value is None else str(value)


def register_jinja_filters(templates: Jinja2Templates) -> None:
    env = templates.env
    env.filters["fmt_dt"] = fmt_dt
    env.filters["fmt_time"] = fmt_time
    env.filters["fmt_none"] = fmt_none
    # Helper global para obtener atributos o claves dinámicamente desde plantillas
    def getv(obj, name, default=""):
        try:
            if obj is None:
                return default
            # Mapping (dict-like)
            if hasattr(obj, "get"):
                return obj.get(name, getattr(obj, name, default))
            return getattr(obj, name, default)
        except Exception:
            return default
    env.globals["getv"] = getv


@lru_cache
def get_templates() -> Jinja2Templates:
    """Devuelve una instancia única de Jinja2Templates con filtros registrados."""
    root = Path(__file__).resolve().parents[2]
    templates_dir = root / "web" / "templates"
    tpl = Jinja2Templates(directory=str(templates_dir))
    register_jinja_filters(tpl)
    return tpl
