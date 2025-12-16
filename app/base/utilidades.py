# Utilidades genéricas para módulos de dominio (nombres en español).
from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel  # type: ignore


def filtrar_campos_permitidos(
    payload: BaseModel | Mapping[str, Any],
    permitidos: Iterable[str],
) -> dict[str, Any]:
    """
    Normaliza la carga útil (BaseModel o Mapping) y devuelve solo los campos permitidos.
    Excluye automáticamente valores None.
    """
    if isinstance(payload, BaseModel):
        datos = payload.model_dump(exclude_none=True)
    else:
        datos = {clave: valor for clave, valor in payload.items() if valor is not None}

    permitidos_set = {campo for campo in permitidos if campo}
    return {campo: valor for campo, valor in datos.items() if campo in permitidos_set}

