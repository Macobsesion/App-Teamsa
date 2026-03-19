"""Modelo SQLModel para proveedores.

Gestiona información de proveedores comerciales, similar a clientes
pero desde la perspectiva de compras.
"""
from sqlmodel import Field, SQLModel, Relationship  # type: ignore
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from app.modulos.servicios_proveedores.servicios_proveedores_modelo import ServicioProveedor

from app.base.auditoria import AuditMixin


from app.modulos.proveedores.proveedores_esquemas import ProveedorBase

class Proveedor(ProveedorBase, AuditMixin, table=True):
    """Proveedor comercial."""
    
    id: int | None = Field(default=None, primary_key=True)

    # Relaciones
    servicios: List["ServicioProveedor"] = Relationship(back_populates="proveedor")

