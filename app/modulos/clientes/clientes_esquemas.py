"""Esquemas Pydantic para clientes."""
from datetime import datetime
from pydantic import BaseModel, Field  # type: ignore


class ClienteBase(BaseModel):
    """Campos comunes de cliente."""
    nombre: str = Field(min_length=1, max_length=200)
    rfc: str | None = Field(default=None, max_length=13)
    razon_social: str | None = None
    contacto: str | None = None
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    estado: str | None = None
    cp: str | None = Field(default=None, max_length=5)
    activo: bool = True
    notas: str | None = None


class ClienteRead(ClienteBase):
    """Schema de lectura (incluye campos de auditoría)."""
    id: int
    creado_por: str
    modificado_por: str | None
    fecha_creacion: datetime
    fecha_modificacion: datetime | None


class ClienteCreate(ClienteBase):
    """Schema para crear cliente."""
    pass


class ClienteUpdate(BaseModel):
    """Schema para actualizar cliente (todos los campos opcionales)."""
    nombre: str | None = None
    rfc: str | None = None
    razon_social: str | None = None
    contacto: str | None = None
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    estado: str | None = None
    cp: str | None = None
    activo: bool | None = None
    notas: str | None = None
