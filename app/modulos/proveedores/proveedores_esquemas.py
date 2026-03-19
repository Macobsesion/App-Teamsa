"""Esquemas Pydantic para proveedores."""
from datetime import datetime
from pydantic import BaseModel
from sqlmodel import SQLModel, Field  # type: ignore


class ProveedorBase(SQLModel):
    """Campos comunes de proveedor."""
    nombre: str = Field(index=True, min_length=1, max_length=200)
    rfc: str | None = Field(default=None, max_length=13)
    razon_social: str | None = None
    contacto: str | None = None
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    cp: str | None = Field(default=None, max_length=5)
    categoria: str | None = None
    activo: bool = Field(default=True)
    notas: str | None = None


class ProveedorRead(ProveedorBase):
    """Schema de lectura (incluye campos de auditoría)."""
    id: int
    creado_por: str
    modificado_por: str | None
    fecha_creacion: datetime
    fecha_modificacion: datetime | None


class ProveedorCreate(ProveedorBase):
    """Schema para crear proveedor."""
    pass


class ProveedorUpdate(BaseModel):
    """Schema para actualizar proveedor (todos los campos opcionales)."""
    nombre: str | None = None
    rfc: str | None = None
    razon_social: str | None = None
    contacto: str | None = None
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    cp: str | None = None
    categoria: str | None = None
    activo: bool | None = None
    notas: str | None = None
