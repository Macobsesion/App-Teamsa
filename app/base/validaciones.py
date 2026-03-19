"""
Validaciones genéricas para composición en descriptores.
"""
from typing import Any, Callable
from app.base.repositorio import RepositorioCRUD

def generador_validador_unicidad(campo: str, custom_message: str | None = None) -> Callable[[RepositorioCRUD, Any], str | None]:
    """
    Genera una función de validación de unicidad para usar en el DescriptorCRUD.
    
    Args:
        campo: Nombre del campo a validar (ej. 'clave', 'codigo_sku', 'rfc')
        custom_message: Mensaje opcional (soporta format field '{valor}')
    """
    def _validador(repo: RepositorioCRUD, payload: Any) -> str | None:
        valor = getattr(payload, campo, None)
        if valor is None:
            return None
            
        if repo.obtener_por_campo(campo, valor):
            if custom_message:
                return custom_message.format(valor=valor)
            return f"Ya existe un registro con {campo} '{valor}'"
        return None
        
    return _validador

__all__ = ["generador_validador_unicidad"]
