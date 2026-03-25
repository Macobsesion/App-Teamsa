"""Esquemas Pydantic para Órdenes de Compra."""
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import List, Optional

class DetalleOrdenCompraBase(BaseModel):
    servicio_proveedor_id: int | None = None
    codigo_sku: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    precio_unitario: Decimal
    descuento_porcentaje: Decimal = Decimal("0.00")

class DetalleOrdenCompraCreate(DetalleOrdenCompraBase):
    pass

class DetalleOrdenCompraRead(DetalleOrdenCompraBase):
    id: int
    importe: Decimal
    cantidad_recibida: Decimal

class OrdenCompraBase(BaseModel):
    proveedor_id: int = Field(title="Proveedor")
    fecha_emision: date = Field(title="Fecha Emisión")
    fecha_entrega_estimada: date | None = None
    metodo_pago: str = "POR_DEFINIR"
    forma_pago: str = "99"
    notas: str | None = None

class OrdenCompraCreate(OrdenCompraBase):
    detalles: List[DetalleOrdenCompraCreate] = []

class OrdenCompraUpdate(BaseModel):
    fecha_emision: date | None = None
    fecha_entrega_estimada: date | None = None
    notas: str | None = None
    notas_privadas: str | None = None
    metodo_pago: str | None = None
    forma_pago: str | None = None
    estado: str | None = None

class OrdenCompraRead(OrdenCompraBase):
    id: int
    folio: str = Field(title="Folio")
    estado: str
    subtotal: Decimal
    iva: Decimal
    total: Decimal
    detalles: List[DetalleOrdenCompraRead] = []

# --- Esquemas para el Wizard (Compatibilidad Frontend) ---

class ItemWizard(BaseModel):
    servicio_id: Optional[int] = Field(None, alias="servicio_proveedor_id")
    codigo: str = Field(..., alias="codigo_sku")
    descripcion: str
    unidad: str
    cantidad: float
    precio_unitario: float
    descuento_porcentaje: float = 0.0

    model_config = {"populate_by_name": True, "from_attributes": True}

class OrdenCompraWizardRead(BaseModel):
    id: int
    folio: str
    proveedor_id: int
    fecha_emision: date
    fecha_entrega: Optional[date] = Field(None, alias="fecha_entrega_estimada")
    metodo_pago: str
    forma_pago: str
    notas: Optional[str] = ""
    estado: str
    items: List[ItemWizard] = Field(..., alias="detalles")

    model_config = {"populate_by_name": True, "from_attributes": True}
