"""Modelos de órdenes de trabajo - SIN precios ni totales."""
from datetime import date, datetime
from decimal import Decimal
from sqlmodel import Field, SQLModel
from app.base.auditoria import AuditMixin


class OrdenTrabajo(AuditMixin, SQLModel, table=True):
    """
    Orden de trabajo generada desde una cotización.
    
    IMPORTANTE: NO incluye precios, descuentos ni totales.
    Solo información técnica de servicios a realizar.
    """
    __tablename__ = "ordentrabajo"
    
    id: int | None = Field(default=None, primary_key=True)
    numero: str = Field(unique=True, index=True, description="Número único: OT-00001")
    
    # Referencias
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    cotizacion_id: int | None = Field(default=None, foreign_key="cotizacion.id")
    
    # Estado y fechas
    estado: str = Field(
        default="pendiente",
        description="Estado: pendiente, programada, en_progreso, completada, cancelada"
    )
    fecha_programada: date | None = None
    fecha_inicio: date | None = None
    fecha_completada: date | None = None
    
    # Asignación
    tecnico_asignado_id: int | None = Field(default=None, foreign_key="usuario.id")
    
    # Notas (solo públicas, NO privadas de cotización)
    notas: str | None = Field(default=None, description="Notas generales copiadas de cotización")
    observaciones_tecnicas: str | None = Field(default=None, description="Observaciones del técnico")
    
    # NO hay campos de: precio, descuento, subtotal, iva, total


class ConceptoOrdenTrabajo(SQLModel, table=True):
    """
    Concepto/servicio de una orden de trabajo.
    
    IMPORTANTE: NO incluye precio_unitario, descuento ni subtotal.
    Solo información técnica: qué hacer y cuánto.
    """
    __tablename__ = "conceptoordentrabajo"
    
    id: int | None = Field(default=None, primary_key=True)
    orden_trabajo_id: int = Field(foreign_key="ordentrabajo.id", index=True)
    
    # Referencia opcional al servicio
    servicio_id: int | None = Field(default=None, foreign_key="servicio.id")
    
    # Información del servicio
    descripcion: str = Field(description="Descripción del servicio a realizar")
    cantidad: Decimal = Field(default=Decimal("1.0"), max_digits=10, decimal_places=2)
    unidad: str = Field(default="Servicio", description="Unidad de medida")
    codigo_unidad: str = Field(default="E48", description="Código SAT de unidad")
    codigo_sat: str | None = Field(default=None, description="Código SAT del servicio")
    
    # NO hay campos de: precio_unitario, descuento_porcentaje, subtotal
