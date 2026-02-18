"""
Objetos de Valor (Value Objects).
Encapsulan grupos de atributos con lógica de validación cohesiva.
"""
from pydantic import BaseModel, field_validator
from typing import Optional

class Direccion(BaseModel):
    """
    Representa una dirección física.
    Es inmutable conceptualmente dentro del dominio.
    """
    calle: Optional[str] = None
    ciudad: Optional[str] = None
    cp: Optional[str] = None
    
    @field_validator("cp")
    @classmethod
    def validar_cp(cls, v: str | None) -> str | None:
        if v and (not v.isdigit() or len(v) != 5):
            # En un sistema real, esto podría ser una ReglaNegocioError
            # pero pydantic maneja sus propios errores de validación.
            raise ValueError("El CP debe ser numérico y de 5 dígitos")
        return v

    def __str__(self) -> str:
        partes = [p for p in [self.calle, self.ciudad, self.cp] if p]
        return ", ".join(partes) if partes else "Sin dirección"
    
    def es_completa(self) -> bool:
        """Devuelve True si la dirección tiene todos sus componentes básicos."""
        return all([self.calle, self.ciudad, self.cp])
