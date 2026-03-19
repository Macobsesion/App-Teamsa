"""Esquemas Pydantic para Servicios de Proveedor."""
from decimal import Decimal
from pydantic import BaseModel
from sqlmodel import SQLModel, Field  # type: ignore

class ServicioProveedorBase(SQLModel):
    proveedor_id: int = Field(foreign_key="proveedor.id", index=True)
    codigo_sku: str = Field(index=True, description="Código SKU del proveedor")
    descripcion: str = Field(description="Nombre o descripción del producto/servicio")
    descripcion_detallada: str | None = Field(default=None, description="Detalles técnicos, dimensiones, etc.")
    costo_unitario: Decimal = Field(default=Decimal("0.00"), decimal_places=2, description="Costo de compra pactado (antes de impuestos)")
    moneda: str = Field(default="MXN", max_length=3)
    unidad: str = Field(default="Pieza", description="Unidad de compra: Caja, Kg, Litro, Hora")
    activo: bool = Field(default=True)

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
