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
    creado_por: str = Field(sa_column_kwargs={"nullable": False})
    # Usuario que modificó por última vez el registro
    modificado_por: str | None = Field(default=None)


from sqlalchemy import event
from app.nucleo.contexto import obtener_usuario_actual

@event.listens_for(AuditMixin, "before_insert", propagate=True)
def _audit_before_insert(mapper, connection, target: AuditMixin):
    """Gatillo automático: asegura que creado_por y modificado_por tengan valor."""
    usuario = obtener_usuario_actual() or "SISTEMA"
    if not target.creado_por:
        target.creado_por = usuario
    if not target.modificado_por:
        target.modificado_por = usuario

@event.listens_for(AuditMixin, "before_update", propagate=True)
def _audit_before_update(mapper, connection, target: AuditMixin):
    """Gatillo automático: actualiza modificado_por en cada cambio."""
    # Solo actualizar si no fue establecido manualmente en esta operación
    usuario = obtener_usuario_actual() or "SISTEMA"
    target.modificado_por = usuario
