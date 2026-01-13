"""Esquemas Pydantic para órdenes de trabajo."""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel


class ConceptoOrdenTrabajoBase(BaseModel):
    """Base para conceptos de orden de trabajo - SIN precios."""
    servicio_id: int | None = None
    descripcion: str
    cantidad: Decimal
    unidad: str = "Servicio"
    codigo_unidad: str = "E48"
    codigo_sat: str | None = None


class ConceptoOrdenTrabajoCreate(ConceptoOrdenTrabajoBase):
    """Crear concepto de orden de trabajo."""
    pass


class ConceptoOrdenTrabajoRead(ConceptoOrdenTrabajoBase):
    """Leer concepto de orden de trabajo."""
    id: int
    orden_trabajo_id: int


class OrdenTrabajoBase(BaseModel):
    """Base para órdenes de trabajo - SIN totales."""
    cliente_id: int
    cotizacion_id: int | None = None
    estado: str = "pendiente"
    fecha_programada: date | None = None
    fecha_inicio: date | None = None
    tecnico_asignado_id: int | None = None
    notas: str | None = None
    observaciones_tecnicas: str | None = None


class OrdenTrabajoCreate(OrdenTrabajoBase):
    """Crear orden de trabajo."""
    pass


class OrdenTrabajoRead(OrdenTrabajoBase):
    """Leer orden de trabajo."""
    id: int
    numero: str
    fecha_creacion: datetime
    fecha_completada: date | None = None
    creado_por: str


class OrdenTrabajoUpdate(BaseModel):
    """Actualizar orden de trabajo."""
    estado: str | None = None
    fecha_programada: date | None = None
    fecha_inicio: date | None = None
    fecha_completada: date | None = None
    tecnico_asignado_id: int | None = None
    notas: str | None = None
    observaciones_tecnicas: str | None = None
