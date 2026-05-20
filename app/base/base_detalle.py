"""
Base para detalles transaccionales.
Centraliza los campos de "Snapshot" y la lógica financiera de partidas.
"""
from decimal import Decimal
from sqlmodel import Field, SQLModel
from pydantic import field_validator
from app.base.auditoria import AuditMixin
from app.base.mixins_financieros import MixinDetalleFinanciero

class BaseDetalleTransaccional(MixinDetalleFinanciero, AuditMixin, SQLModel):
    """
    Clase base abstracta (table=False) para cualquier línea de detalle 
    que requiera persistir un snapshot del catálogo y cálculos financieros.
    """
    # Snapshot de campos descriptivos (comunes a todos los ítems)
    descripcion: str = Field(description="Descripción del servicio/producto al momento de la transacción")
    unidad: str = Field(default="PZ", description="Unidad de medida (PZ, H87, etc)")
    
    # Validadores de seguridad (KISS)
    @field_validator("cantidad", check_fields=False)
    @classmethod
    def validar_cantidad_base(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("La cantidad debe ser mayor a cero")
        return v

    @field_validator("precio_unitario", check_fields=False)
    @classmethod
    def validar_precio_base(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("El precio unitario no puede ser negativo")
        return v

    def recalcular(self) -> None:
        """Asegura el recalcular del importe usando la lógica del mixin."""
        self.calcular_importe()
