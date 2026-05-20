"""Esquemas Pydantic para cotizaciones."""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field as PYField, computed_field  # type: ignore
from sqlmodel import SQLModel, Field # type: ignore
from app.base.mixins_snapshots import SnapshotClienteMixin


# ===== Schemas para Conceptos =====

class ConceptoBase(BaseModel):
    """Campos comunes de concepto."""
    servicio_id: int | None = None
    codigo_sat: str
    descripcion: str
    unidad: str
    cantidad: Decimal = PYField(ge=0, decimal_places=2)
    precio_unitario: Decimal = PYField(ge=0, decimal_places=2)
    descuento_porcentaje: Decimal = PYField(default=Decimal("0.00"), ge=0, le=100, decimal_places=2)
    viatico_id: int | None = None
    viatico_temp_id: int | None = None


class ConceptoRead(ConceptoBase):
    """Schema de lectura de concepto."""
    model_config = {"from_attributes": True}
    
    id: int
    cotizacion_id: int
    importe: Decimal


class ConceptoCreate(ConceptoBase):
    """Schema para crear concepto."""
    pass


# ===== Schemas para Cotizaciones =====

class CotizacionBase(SnapshotClienteMixin, SQLModel):
    """Campos comunes de cotización (Esquema y Tabla)."""
    # Numeración
    numero: str = Field(unique=True, index=True, description="Número con versión: COT-00001 o COT-00001-B")
    numero_version: str = Field(unique=True, index=True, description="Alias de numero (para compatibilidad)")
    
    # Versionamiento
    version_letra: str | None = Field(default=None, description="Letra de versión: None=original, B, C, etc.")
    cotizacion_original_id: int | None = Field(default=None, foreign_key="cotizaciones.id", index=True, description="ID de la cotización original si es versión")
    
    # Datos de negocio específicos
    fecha_vigencia: date | None = Field(default=None, description="Fecha límite de validez de la oferta")
    
    # Relación Viva con cliente
    cliente_id: int = Field(foreign_key="cliente.id", index=True)

    # Nota: Los campos estado, metodo_pago, forma_pago, notas y notas_privadas 
    # se heredan directamente de BaseDocumento en el modelo ORM para evitar duplicidad.


class CotizacionRead(CotizacionBase):
    """Schema de lectura (incluye campos calculados y auditoría)."""
    id: int
    numero: str = PYField(title="Folio")
    cliente_id: int = PYField(title="Cliente")
    
    estado: str = PYField(default="borrador")
    
    # El campo estado_visual se obtendrá del modelo si existe
    estado_visual: str | None = None
    
    numero_version: str  # Campo agregado para versionamiento
    version_letra: str | None = None  # Letra de versión (None, "B", "C", etc.)
    cotizacion_original_id: int | None = None  # FK al original si es versión
    forma_pago: str = PYField(default="99")  # Forma de pago SAT
    
    subtotal: Decimal
    descuento_global: Decimal
    iva: Decimal
    total: Decimal
    fecha_emision: date
    fecha_vigencia: date
    creado_por: str
    modificado_por: str | None
    ejecucion_ot: str | None = PYField(default=None, title="OTs asociadas")
    fecha_creacion: datetime
    fecha_modificacion: datetime | None

    model_config = {"from_attributes": True}


class CotizacionCreate(CotizacionBase):
    """Schema para crear cotización."""
    pass


class CotizacionUpdate(SQLModel):
    """Schema para actualizar cotización (todos los campos opcionales)."""
    cliente_id: int | None = Field(default=None)
    estado: str | None = Field(default=None)
    metodo_pago: str | None = Field(default=None)
    forma_pago: str | None = Field(default=None)
    notas: str | None = Field(default=None)
    notas_privadas: str | None = Field(default=None)
    fecha_vigencia: date | None = Field(default=None)


class CotizacionConConceptos(CotizacionRead):
    """Schema extendido que incluye los conceptos."""
    conceptos: list[ConceptoRead] = []


# --- Esquemas para el Wizard (Compatibilidad Frontend) ---

class CotizacionItemWizard(BaseModel):
    id: int | None = None
    servicio_id: int | None = None
    viatico_id: int | None = None
    descripcion: str
    codigo_sat: str = ""
    unidad: str = "pieza"
    cantidad: float
    precio_unitario: float
    descuento_porcentaje: float = 0.0

    model_config = {"from_attributes": True}


class CotizacionWizardRead(BaseModel):
    id: int
    numero: str
    cliente_id: int
    fecha_emision: date
    fecha_vigencia: date | None = None
    metodo_pago: str = "POR_DEFINIR"
    forma_pago: str = "99"
    notas: str | None = ""
    estado: str = "borrador"
    servicios: list[CotizacionItemWizard] = PYField(..., serialization_alias="servicios", validation_alias="conceptos")

    model_config = {"populate_by_name": True, "from_attributes": True}
