"""Esquemas Pydantic para Servicios de Proveedor."""
from decimal import Decimal
from pydantic import BaseModel, Field

class ServicioProveedorBase(BaseModel):
    proveedor_id: int
    codigo_sku: str
    descripcion: str
    descripcion_detallada: str | None = None
    costo_unitario: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    moneda: str = "MXN"
    unidad: str = "Pieza"
    activo: bool = True

class ServicioProveedorCreate(ServicioProveedorBase):
    pass

class ServicioProveedorUpdate(BaseModel):
    proveedor_id: int | None = None
    codigo_sku: str | None = None
    descripcion: str | None = None
    descripcion_detallada: str | None = None
    costo_unitario: Decimal | None = None
    moneda: str | None = None
    unidad: str | None = None
    activo: bool | None = None

class ServicioProveedorRead(ServicioProveedorBase):
    id: int
    # Campos de auditoría pueden ser agregados
    pass
