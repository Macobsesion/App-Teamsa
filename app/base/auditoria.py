# Mixin de auditoría para modelos SQLModel reutilizable en todas las tablas
# Provee campos estandarizados de trazabilidad: fechas y usuarios de creación/modificación.
from datetime import datetime

from sqlalchemy import DateTime, func  # type: ignore
from sqlmodel import Field, SQLModel  # type: ignore


class AuditMixin(SQLModel, table=False):
    # Fecha/hora de creación (con zona horaria), por defecto del servidor a segundos
    # Importante: usar sa_type + sa_column_kwargs para que SQLModel cree un Column
    # nuevo por cada subclase y evitar reutilización de Column en mixins.
    fecha_creacion: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": func.date_trunc("second", func.now()),
            "nullable": False,
        },
    )
    # Fecha/hora de última modificación (se actualiza automáticamente)
    fecha_modificacion: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "onupdate": func.date_trunc("second", func.now()),
            "nullable": True,
        },
    )
    # Usuario que creó el registro
    creado_por: str
    # Usuario que modificó por última vez el registro
    modificado_por: str | None = Field(default=None)
