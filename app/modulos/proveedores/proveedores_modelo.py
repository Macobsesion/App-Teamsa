"""Modelo SQLModel para proveedores.

Gestiona información de proveedores comerciales, similar a clientes
pero desde la perspectiva de compras.
"""
from sqlmodel import Field, SQLModel  # type: ignore

from app.base.auditoria import AuditMixin


class Proveedor(AuditMixin, SQLModel, table=True):
    """Proveedor comercial."""
    
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
    cp: str | None = Field(default=None, max_length=5)
    
    # Categoría y estado
    categoria: str | None = Field(default=None, description="Tipo de proveedor: materiales, servicios, etc.")
    activo: bool = Field(default=True)
    notas: str | None = None
