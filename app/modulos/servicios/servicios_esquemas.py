"""Esquemas Pydantic para servicios."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field  # type: ignore


class ServicioBase(BaseModel):
    """Campos comunes de servicio."""
    codigo_sat: str = Field(min_length=1, max_length=50)
    codigo_unidad: str = Field(min_length=1, max_length=10)
    clave: str = Field(min_length=1, max_length=50)
    descripcion: str | None = None
    area: str = Field(description="producto o servicio")
    precio_base: Decimal = Field(ge=0, decimal_places=2)
    unidad: str = Field(min_length=1, max_length=50)
    activo: bool = True
    notas: str | None = None


class ServicioRead(ServicioBase):
    """Schema de lectura (incluye campos de auditoría)."""
    id: int
    creado_por: str
    modificado_por: str | None
    fecha_creacion: datetime
    fecha_modificacion: datetime | None


class ServicioCreate(ServicioBase):
    """Schema para crear servicio."""
    pass


class ServicioUpdate(BaseModel):
    """Schema para actualizar servicio (todos los campos opcionales)."""
    codigo_sat: str | None = None
    codigo_unidad: str | None = None
    clave: str | None = None
    descripcion: str | None = None
    area: str | None = None  # Cambiado de 'tipo' a 'area'
    precio_base: Decimal | None = None
    unidad: str | None = None
    activo: bool | None = None
    notas: str | None = None
