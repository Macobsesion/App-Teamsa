"""Modelo SQLModel para clientes.
"""
from sqlmodel import Field, SQLModel, Relationship  # type: ignore

from app.base.auditoria import AuditMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion

import re
from pydantic import field_validator, EmailStr
from app.base.valores import Direccion
from app.modulos.clientes.clientes_esquemas import ClienteBase


class Cliente(ClienteBase, AuditMixin, table=True):
    """Cliente comercial."""
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Configuración para evitar errores de Pydantic v2 con Value Objects no anotados
    model_config = {"ignored_types": (Direccion,)} # type: ignore

    @field_validator("rfc", check_fields=False)
    @classmethod
    def validar_rfc(cls, v: str | None) -> str | None:
        if v:
            v = v.upper().strip()
            # Patrón para RFC de Persona Física o Moral
            if not re.match(r"^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$", v):
                raise ValueError("Formato de RFC inválido (Ej: XXXX991231XXX)")
        return v

    @field_validator("email", check_fields=False)
    @classmethod
    def validar_email(cls, v: str | None) -> str | None:
        if v:
            v = v.lower().strip()
            if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
                raise ValueError("Formato de email inválido")
        return v

    @field_validator("cp", check_fields=False)
    @classmethod
    def validar_cp(cls, v: str | None) -> str | None:
        if v:
            v = v.strip()
            if not re.match(r"^[0-9]{5}$", v):
                raise ValueError("El código postal debe tener 5 dígitos")
        return v
    
    # Relaciones
    cotizaciones: list["Cotizacion"] = Relationship(back_populates="cliente")
    
    # ---- PROPIEDADES COMPUESTAS (Value Objects) ----
    
    @property
    def direccion_vo(self) -> Direccion:
        """Devuelve la dirección como un Objeto de Valor."""
        return Direccion(
            calle=self.direccion,
            ciudad=self.ciudad,
            cp=self.cp
        )
    
    @direccion_vo.setter
    def direccion_vo(self, valor: Direccion) -> None:
        """Asigna la dirección descomponiendo el Objeto de Valor en columnas planas."""
        self.direccion = valor.calle
        self.ciudad = valor.ciudad
        self.cp = valor.cp
