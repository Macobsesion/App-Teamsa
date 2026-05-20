"""Esquemas de transferencia de Viáticos."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class ViaticoBase(BaseModel):
    cliente_id: int
    responsable_id: int
    proyecto: Optional[str] = None
    
    ot_ids: list[int] = Field(default_factory=list, description="OTs asociadas")
    
    personas: int = Field(default=1, ge=1)
    tipo_transporte: Optional[str] = None
    cotizacion_id: Optional[int] = None
    origen: Optional[str] = None
    destino: Optional[str] = None
    fecha_salida: Optional[date] = None
    fecha_regreso: Optional[date] = None

    costo_transporte: Decimal = Field(default=Decimal("0.00"), ge=0)
    costo_alojamiento: Decimal = Field(default=Decimal("0.00"), ge=0)
    costo_alimentos: Decimal = Field(default=Decimal("0.00"), ge=0)
    costo_otros: Decimal = Field(default=Decimal("0.00"), ge=0)
    
    notas_desglose: Optional[str] = None
    estado: str = "borrador"

    @field_validator("costo_transporte", "costo_alojamiento", "costo_alimentos", "costo_otros", mode="before")
    @classmethod
    def cast_empty_cost(cls, v):
        if v == "" or v is None:
            return Decimal("0.00")
        return v

    @field_validator("personas", mode="before")
    @classmethod
    def cast_empty_personas(cls, v):
        if v == "" or v is None:
            return 1
        return int(v)

class ViaticoCreate(ViaticoBase):
    pass

class ViaticoUpdate(BaseModel):
    cliente_id: Optional[int] = None
    responsable_id: Optional[int] = None
    proyecto: Optional[str] = None
    ot_ids: Optional[list[int]] = None
    personas: Optional[int] = None
    tipo_transporte: Optional[str] = None
    cotizacion_id: Optional[int] = None
    origen: Optional[str] = None
    destino: Optional[str] = None
    fecha_salida: Optional[date] = None
    fecha_regreso: Optional[date] = None
    costo_transporte: Optional[Decimal] = None
    costo_alojamiento: Optional[Decimal] = None
    costo_alimentos: Optional[Decimal] = None
    costo_otros: Optional[Decimal] = None
    notas_desglose: Optional[str] = None
    estado: Optional[str] = None

class ViaticoRead(ViaticoBase):
    id: int
    folio: str
    total: Decimal
    
    creado_por: str
    modificado_por: Optional[str]
    fecha_creacion: datetime
    fecha_modificacion: Optional[datetime]

    model_config = {"from_attributes": True}
