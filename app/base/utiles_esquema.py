"""Utilidades para introspección de esquemas Pydantic (nombres en español)."""
from __future__ import annotations

from typing import Any, Iterable

from pydantic import BaseModel  # type: ignore


def obtener_columnas_schema(
    schema: type[BaseModel],
    *,
    incluir: Iterable[str] | None = None,
    excluir: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Genera metadata de columnas a partir de un esquema Pydantic.

    Respeta el orden de `incluir` cuando se provee (evita desalinear encabezados
    con las filas renderizadas), y si no, usa el orden del schema.
    """
    props: dict[str, Any] = schema.model_json_schema().get("properties", {})
    exclude_set = set(excluir) if excluir else set()

    if incluir is not None:
        names = list(incluir)  # preservar orden definido por el descriptor
    else:
        names = list(props.keys())

    columnas: list[dict[str, Any]] = []
    for nombre in names:
        if nombre in exclude_set:
            continue
        info = props.get(nombre)
        if isinstance(info, dict):
            columnas.append({
                "campo": nombre,
                "titulo": info.get("title", nombre.replace("_", " ").title()),
                "tipo": info.get("type"),
            })
        else:
            # Columna virtual (no en el schema)
            columnas.append({
                "campo": nombre,
                "titulo": nombre.replace("_", " ").title(),
                "tipo": "string",
            })
    return columnas


def _json_schema(schema: type[BaseModel]) -> dict[str, Any]:
    try:
        return schema.model_json_schema()
    except Exception:
        return {}


def obtener_campos_creables(schema: type[BaseModel]) -> list[str]:
    """Lista simple de nombres de campos definidos en el esquema de creación."""
    props = _json_schema(schema).get("properties", {})
    return list(props.keys())


def obtener_campos_requeridos(schema: type[BaseModel]) -> list[str]:
    """Campos marcados como requeridos por el esquema (según JSON Schema)."""
    return list(_json_schema(schema).get("required", []) or [])


def obtener_tipos_propiedades(schema: type[BaseModel]) -> dict[str, dict[str, Any]]:
    """Mapa nombre -> {type, format} según JSON Schema, útil para normalización en el frontend."""
    props = _json_schema(schema).get("properties", {})
    resultado: dict[str, dict[str, Any]] = {}
    for nombre, info in props.items():
        resultado[nombre] = {
            "type": info.get("type"),
            "format": info.get("format"),
        }
    return resultado

__all__ = [
    "obtener_columnas_schema",
    "obtener_campos_creables",
    "obtener_campos_requeridos",
    "obtener_tipos_propiedades",
]
