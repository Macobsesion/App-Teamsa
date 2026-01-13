"""Esquemas Pydantic para cotizaciones."""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, computed_field  # type: ignore


# ===== Schemas para Conceptos =====

class ConceptoBase(BaseModel):
    """Campos comunes de concepto."""
    servicio_id: int | None = None
    codigo_sat: str
    descripcion: str
    unidad: str
    cantidad: Decimal = Field(ge=0, decimal_places=2)
    precio_unitario: Decimal = Field(ge=0, decimal_places=2)
    descuento_porcentaje: Decimal = Field(default=Decimal("0.00"), ge=0, le=100, decimal_places=2)


class ConceptoRead(ConceptoBase):
    """Schema de lectura de concepto."""
    id: int
    cotizacion_id: int
    importe: Decimal


class ConceptoCreate(ConceptoBase):
    """Schema para crear concepto."""
    pass


# ===== Schemas para Cotizaciones =====

class CotizacionBase(BaseModel):
    """Campos comunes de cotización."""
    cliente_id: int
    estado: str = Field(default="borrador")
    metodo_pago: str = Field(default="POR_DEFINIR")
    notas: str | None = None
    notas_privadas: str | None = None  # Notas internas (no visibles en PDF)


class CotizacionRead(CotizacionBase):
    """Schema de lectura (incluye campos calculados y auditoría)."""
    id: int
    numero: str
    numero_version: str  # Campo agregado para versionamiento
    version_letra: str | None = None  # Letra de versión (None, "B", "C", etc.)
    cotizacion_original_id: int | None = None  # FK al original si es versión
    forma_pago: str = Field(default="99")  # Forma de pago SAT
    subtotal: Decimal
    descuento_global: Decimal
    iva: Decimal
    total: Decimal
    fecha_emision: date
    fecha_vigencia: date
    creado_por: str
    modificado_por: str | None
    fecha_creacion: datetime
    fecha_modificacion: datetime | None


class CotizacionCreate(CotizacionBase):
    """Schema para crear cotización."""
    pass


class CotizacionUpdate(BaseModel):
    """Schema para actualizar cotización (todos los campos opcionales)."""
    cliente_id: int | None = None
    estado: str | None = None
    metodo_pago: str | None = None
    notas: str | None = None
    notas_privadas: str | None = None  # Permitir actualizar notas privadas


class CotizacionConConceptos(CotizacionRead):
    """Schema extendido que incluye los conceptos."""
    conceptos: list[ConceptoRead] = []
