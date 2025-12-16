"""Esquemas Pydantic para viáticos."""
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field  # type: ignore


# ===== Schemas para Gastos =====

class GastoBase(BaseModel):
    """Campos comunes de gasto."""
    categoria: str = Field(description="transporte, alojamiento, alimentos, otros")
    concepto: str
    cantidad: Decimal = Field(ge=0, decimal_places=2)
    precio_unitario: Decimal = Field(ge=0, decimal_places=2)
    fecha_gasto: date
    tiene_factura: bool = False
    numero_factura: str | None = None


class GastoRead(GastoBase):
    """Schema de lectura de gasto."""
    id: int
    viatico_id: int
    importe: Decimal


class GastoCreate(GastoBase):
    """Schema para crear gasto."""
    pass


# ===== Schemas para Viáticos =====

class ViaticoBase(BaseModel):
    """Campos comunes de viático."""
    responsable_id: int
    proyecto: str
    cliente: str
    destino: str
    fecha_inicio: date
    fecha_fin: date
    estado: str = Field(default="borrador")
    notas: str | None = None
    observaciones: str | None = None


class ViaticoRead(ViaticoBase):
    """Schema de lectura (incluye campos calculados y auditoría)."""
    id: int
    numero: str
    dias: int
    total_transporte: Decimal
    total_alojamiento: Decimal
    total_alimentos: Decimal
    total_otros: Decimal
    total_general: Decimal
    creado_por: str
    modificado_por: str | None
    fecha_creacion: date
    fecha_modificacion: date | None


class ViaticoCreate(ViaticoBase):
    """Schema para crear viático."""
    pass


class ViaticoUpdate(BaseModel):
    """Schema para actualizar viático (todos los campos opcionales)."""
    responsable_id: int | None = None
    proyecto: str | None = None
    cliente: str | None = None
    destino: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    estado: str | None = None
    notas: str | None = None
    observaciones: str | None = None


class ViaticoConGastos(ViaticoRead):
    """Schema extendido que incluye los gastos."""
    gastos: list[GastoRead] = []
