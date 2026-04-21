from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel  # type: ignore

class LogActividad(SQLModel, table=True):
    """Modelo para registrar la actividad de los usuarios en el sistema (Auditoría)."""
    __tablename__ = "logs_actividad"

    id: Optional[int] = Field(default=None, primary_key=True)
    fecha: datetime = Field(
        default_factory=datetime.now,
        index=True,
        description="Fecha y hora del evento"
    )
    usuario: str = Field(index=True, description="Nombre de usuario que realizó la acción")
    accion: str = Field(index=True, description="Tipo de acción: CREAR, EDITAR, ELIMINAR, LOGIN, etc.")
    modulo: str = Field(index=True, description="Módulo afectado (ej: clientes, cotizaciones)")
    detalles: Optional[str] = Field(default=None, description="Descripción adicional o ID del recurso")
    ip: Optional[str] = Field(default=None, description="Dirección IP del cliente")

    model_config = {
        "from_attributes": True
    }
