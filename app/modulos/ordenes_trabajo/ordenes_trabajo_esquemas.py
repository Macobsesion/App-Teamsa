"""Esquemas Pydantic para Ordenes de Trabajo."""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel
from sqlmodel import SQLModel, Field  # type: ignore


class ConceptoOTRead(BaseModel):
    """Lectura pública de un concepto de OT — sin precios (uso en API general)."""
    id: int
    concepto_cotizacion_id: int
    descripcion: str
    cantidad: Decimal
    unidad: str
    estado: str  # "pendiente" | "completado"
    fecha_completado: datetime | None = None
    completado_por: str | None = None

    model_config = {"from_attributes": True}


class ConceptoOTReadInterno(ConceptoOTRead):
    """Lectura interna de un concepto de OT — incluye campos monetarios (uso admin)."""
    precio_unitario: Decimal
    importe: Decimal


class OrdenTrabajoBase(SQLModel):
    """Atributos base compartidos entre Esquemas y Modelo (Regla 1.10)."""
    fecha_programada: date = Field(description="Día del servicio")
    hora_programada: str = Field(description="Hora de inicio programada (HH:MM)")
    duracion: int = Field(default=1, description="Duración estimada")
    unidad_duracion: str = Field(default="horas", description="Unidad de duración")
    domicilio: str = Field(description="Domicilio del servicio")
    contacto: str = Field(description="Nombre del contacto")
    estado: str = Field(default="programada", index=True)
    notas_publicas: str | None = Field(default=None, description="Notas para el PDF")
    notas_privadas: str | None = Field(default=None, description="Notas internas")


class OrdenTrabajoCreate(OrdenTrabajoBase):
    """Datos necesarios para crear una OT desde una cotización."""
    cotizacion_id: int
    cliente_nombre: str
    tecnico_id: int | None = None
    concepto_ids: list[int] = []


class OrdenTrabajoUpdate(SQLModel):
    """Campos editables de una OT (todos opcionales para PATCH)."""
    fecha_programada: date | None = None
    hora_programada: str | None = None
    duracion: int | None = None
    domicilio: str | None = None
    contacto: str | None = None
    estado: str | None = None
    tecnico_id: int | None = None
    notas_publicas: str | None = None
    notas_privadas: str | None = None


class OrdenTrabajoRead(OrdenTrabajoBase):
    """Esquema completo para lectura (incluye IDs y Auditoría)."""
    id: int
    numero_ot: str
    estado_visual: str | None = None
    cotizacion_id: int
    cliente_nombre: str
    tecnico_id: int | None = None
    tecnico_nombre: str | None = None
    # Relación de conceptos (esquema público sin precios por seguridad)
    conceptos: list[ConceptoOTRead] = []

    # Auditoría
    creado_por: str
    fecha_creacion: datetime
    modificado_por: str | None = None
    fecha_modificacion: datetime | None = None

    model_config = {"from_attributes": True}
