"""Modelo SQLModel para clientes.
"""
from sqlmodel import Field, SQLModel  # type: ignore

from app.base.auditoria import AuditMixin


class Cliente(AuditMixin, SQLModel, table=True):
    """Cliente comercial."""
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Datos básicos
    nombre: str = Field(index=True)
    rfc: str | None = Field(default=None, max_length=13)
    razon_social: str | None = None
    
    # Contacto
    contacto: str | None = None
    email: str | None = None
    telefono: str | None = None
    
    # Dirección
    direccion: str | None = None
    ciudad: str | None = None
    estado: str | None = None
    cp: str | None = Field(default=None, max_length=5)
    
    # Estado
    activo: bool = Field(default=True)
    notas: str | None = None
