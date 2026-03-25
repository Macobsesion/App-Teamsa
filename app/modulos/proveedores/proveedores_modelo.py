"""Modelo SQLModel para proveedores.

Gestiona información de proveedores comerciales, similar a clientes
pero desde la perspectiva de compras.
"""
from sqlmodel import Field, SQLModel, Relationship  # type: ignore
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from app.modulos.servicios_proveedores.servicios_proveedores_modelo import ServicioProveedor

from app.base.auditoria import AuditMixin


import re
from pydantic import field_validator
from app.modulos.proveedores.proveedores_esquemas import ProveedorBase

class Proveedor(ProveedorBase, AuditMixin, table=True):
    """Proveedor comercial."""
    
    id: int | None = Field(default=None, primary_key=True)

    @field_validator("rfc", check_fields=False)
    @classmethod
    def validar_rfc(cls, v: str | None) -> str | None:
        if v:
            v = v.upper().strip()
            if not re.match(r"^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$", v):
                raise ValueError("Formato de RFC inválido")
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
    servicios: List["ServicioProveedor"] = Relationship(back_populates="proveedor")

