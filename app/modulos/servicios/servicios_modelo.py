"""Modelo SQLModel para servicios y productos.

Incluye códigos del SAT para facturación electrónica en México.
"""
from decimal import Decimal
from sqlmodel import Field, SQLModel  # type: ignore

from app.base.auditoria import AuditMixin


from app.modulos.servicios.servicios_esquemas import ServicioBase

class Servicio(ServicioBase, AuditMixin, table=True):
    """Servicio o producto del catálogo."""
    
    id: int | None = Field(default=None, primary_key=True)
