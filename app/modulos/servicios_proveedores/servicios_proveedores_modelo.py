"""Modelo SQLModel para Servicios de Proveedor.
Artículos o servicios que la empresa compra a sus proveedores.
"""
from decimal import Decimal
from sqlmodel import Field, SQLModel, Relationship # type: ignore
from typing import Optional, TYPE_CHECKING

from app.base.auditoria import AuditMixin

if TYPE_CHECKING:
    from app.modulos.proveedores.proveedores_modelo import Proveedor

class ServicioProveedor(AuditMixin, SQLModel, table=True):
    """Ítem del catálogo de compra (Producto/Servicio de un Proveedor)."""
    __tablename__ = "servicio_proveedor"

    id: int | None = Field(default=None, primary_key=True)

    # Relación obligatoria con Proveedor
    proveedor_id: int = Field(foreign_key="proveedor.id", index=True)
    
    # Identificación del producto
    codigo_sku: str = Field(index=True, description="Código SKU del proveedor")
    descripcion: str = Field(description="Nombre o descripción del producto/servicio")
    descripcion_detallada: str | None = Field(default=None, description="Detalles técnicos, dimensiones, etc.")
    
    # Datos económicos
    costo_unitario: Decimal = Field(default=Decimal("0.00"), decimal_places=2, description="Costo de compra pactado (antes de impuestos)")
    moneda: str = Field(default="MXN", max_length=3)
    
    # Unidad de medida de compra (puede ser diferente a la de venta)
    unidad: str = Field(default="Pieza", description="Unidad de compra: Caja, Kg, Litro, Hora")
    
    # Estado
    activo: bool = Field(default=True)
    
    # Relaciones
    proveedor: "Proveedor" = Relationship(back_populates="servicios")
