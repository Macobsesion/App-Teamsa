"""
Utilidades para Pydantic y procesamiento de formularios.
"""
from typing import Any
from pydantic import BeforeValidator # type: ignore
from typing_extensions import Annotated # type: ignore

def _string_vacio_a_none(v: Any) -> Any:
    """Validador 'Before' para Pydantic. 
    Convierte cadenas vacías (que llegan típicas de Formularios HTML HTMX) a None
    antes de que Pydantic intente parsearlas a int, float o date.
    """
    if isinstance(v, str) and v.strip() == "":
        return None
    return v

# Tipo anotado reusable para modelos Pydantic
# Uso: `edad: EmptyStrAsNone[int | None] = None`
EmptyStrAsNone = Annotated[Any, BeforeValidator(_string_vacio_a_none)]
