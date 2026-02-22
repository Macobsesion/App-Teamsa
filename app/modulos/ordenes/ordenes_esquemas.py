"""Esquemas Pydantic para Ordenes de Trabajo."""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel


class ConceptoOTRead(BaseModel):
    """Lectura de un concepto de OT con su estado."""
    id: int
    concepto_cotizacion_id: int
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    importe: Decimal
    unidad: str
    estado: str  # "pendiente" | "completado"
    fecha_completado: datetime | None = None
    completado_por: str | None = None

    model_config = {"from_attributes": True}


class OrdenTrabajoBase(BaseModel):
    fecha_programada: date
    hora_programada: str
    duracion: int = 1
    domicilio: str
    contacto: str
    notas_publicas: str | None = None
    notas_privadas: str | None = None


class OrdenTrabajoCreate(OrdenTrabajoBase):
    """Datos necesarios para crear una OT desde una cotización."""
    cotizacion_id: int
    cliente_nombre: str
    tecnico_id: int | None = None
    concepto_ids: list[int] = []


class OrdenTrabajoUpdate(BaseModel):
    """Campos editables de una OT."""
    fecha_programada: date | None = None
    hora_programada: str | None = None
    domicilio: str | None = None
    contacto: str | None = None
    estado: str | None = None
    tecnico_id: int | None = None
    notas_publicas: str | None = None
    notas_privadas: str | None = None


class OrdenTrabajoRead(OrdenTrabajoBase):
    id: int
    numero_ot: str
    cotizacion_id: int
    cliente_nombre: str
    estado: str
    tecnico_id: int | None = None
    tecnico_nombre: str | None = None
    conceptos: list[ConceptoOTRead] = []

    # Auditoría
    creado_por: str
    fecha_creacion: datetime
    modificado_por: str | None = None
    fecha_modificacion: datetime | None = None

    model_config = {"from_attributes": True}
