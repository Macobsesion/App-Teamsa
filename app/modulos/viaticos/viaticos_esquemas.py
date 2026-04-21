"""Esquemas de transferencia de Viáticos."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator

from sqlmodel import SQLModel, Field  # type: ignore
from app.base.mixins_snapshots import SnapshotClienteMixin

class ViaticoBase(SnapshotClienteMixin, SQLModel):
    """Campos base para Viáticos."""
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    responsable_id: int = Field(foreign_key="usuario.id", index=True)
    proyecto: str | None = Field(default=None, max_length=200)
    
    
    personas: int = Field(default=1, ge=1)
    tipo_transporte: str | None = Field(default=None, max_length=100)
    cotizacion_id: int | None = Field(default=None, foreign_key="cotizaciones.id", index=True)
    origen: str | None = Field(default=None, max_length=100)
    destino: str | None = Field(default=None, max_length=100)
    fecha_salida: date | None = Field(default=None, title="Fecha Salida")
    fecha_regreso: date | None = Field(default=None, title="Fecha Regreso")
    dias: int = Field(default=1, ge=1, title="Días")

    # Costos
    costo_transporte: Decimal = Field(default=Decimal("0.00"), ge=0)
    costo_alojamiento: Decimal = Field(default=Decimal("0.00"), ge=0)
    
    # Desglose de Alimentos
    desayuno: Decimal = Field(default=Decimal("0.00"), ge=0)
    comida: Decimal = Field(default=Decimal("0.00"), ge=0)
    cena: Decimal = Field(default=Decimal("0.00"), ge=0)

    costo_alimentos: Decimal = Field(default=Decimal("0.00"), ge=0)
    costo_otros: Decimal = Field(default=Decimal("0.00"), ge=0)
    
    notas_desglose: str | None = Field(default=None)
    estado: str = Field(default="borrador", index=True)

    @field_validator("costo_transporte", "costo_alojamiento", "costo_alimentos", "costo_otros", mode="before")
    @classmethod
    def cast_empty_cost(cls, v: Any) -> Decimal:
        if v == "" or v is None:
            return Decimal("0.00")
        return Decimal(str(v))

    @field_validator("personas", mode="before")
    @classmethod
    def cast_empty_personas(cls, v: Any) -> int:
        if v == "" or v is None:
            return 1
        return int(v)

class ViaticoCreate(ViaticoBase):
    """Esquema para creación."""
    ot_ids: list[int] = Field(default_factory=list)

class ViaticoUpdate(SQLModel):
    """Esquema para actualización (campos opcionales).
    Mantenemos explícito para evitar 'magia' y asegurar autocompletado (Regla 1).
    """
    cliente_id: int | None = None
    responsable_id: int | None = None
    proyecto: str | None = None
    ot_ids: list[int] | None = None
    personas: int | None = None
    tipo_transporte: str | None = None
    cotizacion_id: int | None = None
    origen: str | None = None
    destino: str | None = None
    fecha_salida: date | None = None
    fecha_regreso: date | None = None
    dias: int | None = None
    costo_transporte: Decimal | None = None
    costo_alojamiento: Decimal | None = None
    costo_alimentos: Decimal | None = None
    costo_otros: Decimal | None = None
    notas_desglose: str | None = None
    estado: str | None = None

class ViaticoRead(ViaticoBase):
    """Esquema para lectura."""
    id: int
    folio: str
    total: Decimal
    
    creado_por: str
    modificado_por: str | None
    fecha_creacion: datetime
    fecha_modificacion: datetime | None

    model_config = {"from_attributes": True} # type: ignore
