"""Esquemas Pydantic para Órdenes de Compra."""
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import List

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
    fecha_entrega_estimada: date | None = None
    notas: str | None = None
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
