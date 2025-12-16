"""Modelo SQLModel para servicios y productos.

Incluye códigos del SAT para facturación electrónica en México.
"""
from decimal import Decimal
from sqlmodel import Field, SQLModel  # type: ignore

from app.base.auditoria import AuditMixin


class Servicio(AuditMixin, SQLModel, table=True):
    """Servicio o producto del catálogo."""
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Códigos SAT para facturación electrónica
    codigo_sat: str = Field(index=True, description="Código de producto/servicio SAT")
    
    # Identificación interna
    clave: str = Field(unique=True, index=True, description="Clave interna del servicio/producto")
    descripcion: str | None = None
    area: str = Field(description="Área de aplicación del servicio")
    
    # Precio y unidad
    precio_base: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    unidad: str = Field(description="Nombre de la unidad: pieza, hora, m2, etc.")
    codigo_unidad: str = Field(index=True, description="Código de unidad de medida SAT (H87, E48, etc.)")
    
    # Estado
    activo: bool = Field(default=True)
    notas: str | None = None
