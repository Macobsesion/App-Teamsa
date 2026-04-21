"""Modelos para Órdenes de Compra."""
from decimal import Decimal
from datetime import date
from enum import Enum
from app.base.valores import Direccion
from sqlmodel import Field, SQLModel, Relationship
from pydantic import field_validator, model_validator
from typing import List, Optional, TYPE_CHECKING

from app.base.documentos_modelo import BaseDocumento
from app.base.mixins_financieros import MixinDetalleFinanciero
from app.base.mixins_snapshots import SnapshotProveedorMixin
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

    @property
    def es_editable(self) -> bool:
        """Determina si la OC puede ser editada."""
        return self == EstadoOrdenCompra.BORRADOR

    @property
    def es_cancelable(self) -> bool:
        """Determina si la OC puede ser cancelada."""
        return self not in (EstadoOrdenCompra.CANCELADA, EstadoOrdenCompra.RECIBIDA)

class OrdenCompra(SnapshotProveedorMixin, BaseDocumento, table=True):
    """Encabezado de la Orden de Compra."""
    __tablename__ = "orden_compra"

    id: int | None = Field(default=None, primary_key=True)
    
    # MIXIN: SnapshotProveedorMixin incluye proveedor_nombre, proveedor_rfc, etc. y direccion_proveedor_vo
    
    # Proveedor Relación Viva (Para métricas y catálogos)
    proveedor_id: int = Field(foreign_key="proveedor.id", index=True)
    
    # Datos generales
    fecha_entrega_estimada: date | None = None
    
    @model_validator(mode="after")
    def validar_fechas(self) -> "OrdenCompra":
        if self.fecha_entrega_estimada and self.fecha_emision:
            if self.fecha_entrega_estimada < self.fecha_emision:
                raise ValueError("La fecha de entrega estimada no puede ser anterior a la de emisión")
        return self
    
    # MIXIN: BaseDocumento incluye fecha_emision, folio, estado, metodo_pago, forma_pago, notas, notas_privadas
    
    # Relaciones
    proveedor: "Proveedor" = Relationship()
    detalles: List["DetalleOrdenCompra"] = Relationship(back_populates="orden", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    @property
    def estado_enum(self) -> EstadoOrdenCompra:
        return EstadoOrdenCompra(self.estado)


from app.base.base_detalle import BaseDetalleTransaccional

class DetalleOrdenCompra(BaseDetalleTransaccional, table=True):
    """Partida individual de la orden de compra."""
    __tablename__ = "detalle_orden_compra"

    id: int | None = Field(default=None, primary_key=True)

    orden_id: int = Field(foreign_key="orden_compra.id", index=True)
    
    # Referencia al catálogo de compra
    servicio_proveedor_id: int | None = Field(default=None, foreign_key="servicio_proveedor.id", index=True)
    
    # Descripción snapshot (por si cambia el catálogo) / heredado: descripcion, unidad
    codigo_sku: str
    
    # Cantidades (cantidad viene de BaseDetalleTransaccional)
    cantidad_recibida: Decimal = Field(default=Decimal("0.0"), decimal_places=2)
    
    # Relaciones
    orden: OrdenCompra = Relationship(back_populates="detalles")
    servicio_original: Optional["ServicioProveedor"] = Relationship()
