"""Esquemas Pydantic para Ordenes de Trabajo."""
from datetime import date, time, datetime
from pydantic import BaseModel, Field

class OrdenTrabajoBase(BaseModel):
    fecha_programada: date
    hora_programada: time
    duracion: int = 1
    domicilio: str
    contacto: str
    notas_publicas: str | None = None
    notas_privadas: str | None = None

class OrdenTrabajoCreate(OrdenTrabajoBase):
    """Datos necesarios para crear una OT desde una cotización."""
    cotizacion_id: int
    cliente_nombre: str

class OrdenTrabajoUpdate(BaseModel):
    """Campos editables de una OT."""
    fecha_programada: date | None = None
    hora_programada: time | None = None
    domicilio: str | None = None
    contacto: str | None = None
    estado: str | None = None
    notas_publicas: str | None = None
    notas_privadas: str | None = None

class OrdenTrabajoRead(OrdenTrabajoBase):
    id: int
    numero_ot: str
    cotizacion_id: int
    cliente_nombre: str
    estado: str
    
    # Auditoría
    creado_por: str
    fecha_creacion: datetime
    modificado_por: str | None = None
    fecha_modificacion: datetime | None = None

    model_config = {"from_attributes": True}
