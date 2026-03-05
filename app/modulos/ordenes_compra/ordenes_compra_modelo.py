"""Modelos para Órdenes de Compra."""
from decimal import Decimal
from datetime import date
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship
from typing import List, Optional, TYPE_CHECKING

from app.base.documentos_modelo import BaseDocumento
from app.base.mixins_financieros import MixinDetalleFinanciero
from typing import TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from app.modulos.proveedores.proveedores_modelo import Proveedor
    from app.modulos.servicios_proveedores.servicios_proveedores_modelo import ServicioProveedor

class EstadoOrdenCompra(str, Enum):
    BORRADOR = "borrador"
    EMITIDA = "emitida" # Enviada al proveedor
    PARCIALMENTE_RECIBIDA = "parcial"
    RECIBIDA = "recibida" # Completa
    CANCELADA = "cancelada"

class OrdenCompra(BaseDocumento, table=True):
    """Encabezado de la Orden de Compra."""
    __tablename__ = "orden_compra"

    id: int | None = Field(default=None, primary_key=True)
    
    # Snapshot del Proveedor (Congelamiento Histórico)
    proveedor_nombre: str | None = Field(default=None, description="Nombre del proveedor al momento de la orden")
    proveedor_rfc: str | None = Field(default=None, max_length=13, description="RFC del proveedor")
    proveedor_direccion: str | None = Field(default=None, description="Dirección capturada")
    proveedor_ciudad: str | None = Field(default=None, description="Ciudad capturada")
    proveedor_cp: str | None = Field(default=None, max_length=5, description="Código postal capturado")
    proveedor_telefono: str | None = Field(default=None, description="Teléfono capturado")
    proveedor_email: str | None = Field(default=None, description="Email capturado")
    
    # Proveedor Relación Viva (Para métricas y catálogos)
    proveedor_id: int = Field(foreign_key="proveedor.id", index=True)
    
    # Datos generales
    fecha_entrega_estimada: date | None = None
    
    # MIXIN: BaseDocumento incluye fecha_emision, folio, estado, metodo_pago, forma_pago, notas, notas_privadas
    
    # Relaciones
    proveedor: "Proveedor" = Relationship()
    detalles: List["DetalleOrdenCompra"] = Relationship(back_populates="orden", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    @property
    def estado_enum(self) -> EstadoOrdenCompra:
        return EstadoOrdenCompra(self.estado)


class DetalleOrdenCompra(MixinDetalleFinanciero, SQLModel, table=True):
    """Partida individual de la orden de compra."""
    __tablename__ = "detalle_orden_compra"

    id: int | None = Field(default=None, primary_key=True)
    orden_id: int = Field(foreign_key="orden_compra.id", index=True)
    
    # Referencia al catálogo de compra
    servicio_proveedor_id: int | None = Field(default=None, foreign_key="servicio_proveedor.id", index=True)
    
    # Descripción snapshot (por si cambia el catálogo)
    codigo_sku: str
    descripcion: str
    unidad: str
    
    # Cantidades
    # Cantidades (cantidad viene del MixinDetalleFinanciero y representa lo solicitado)
    # cantidad_solicitada eliminada en favor de self.cantidad heredada
    cantidad_recibida: Decimal = Field(default=Decimal("0.0"), decimal_places=2)
    
    # Relaciones
    orden: OrdenCompra = Relationship(back_populates="detalles")
    servicio_original: Optional["ServicioProveedor"] = Relationship()
