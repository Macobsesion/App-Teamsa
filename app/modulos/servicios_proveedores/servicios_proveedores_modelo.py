"""Modelo SQLModel para Servicios de Proveedor.
Artículos o servicios que la empresa compra a sus proveedores.
"""
from decimal import Decimal
from sqlmodel import Field, SQLModel, Relationship # type: ignore
from typing import Optional, TYPE_CHECKING

from app.base.auditoria import AuditMixin

if TYPE_CHECKING:
    from app.modulos.proveedores.proveedores_modelo import Proveedor

from app.modulos.servicios_proveedores.servicios_proveedores_esquemas import ServicioProveedorBase

class ServicioProveedor(ServicioProveedorBase, AuditMixin, table=True):
    """Ítem del catálogo de compra (Producto/Servicio de un Proveedor)."""
    __tablename__ = "servicio_proveedor"

    id: int | None = Field(default=None, primary_key=True)

    # Relaciones
    proveedor: "Proveedor" = Relationship(back_populates="servicios")
