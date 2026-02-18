"""Modelo base para Documentos Financieros (Cotizaciones, Órdenes de Compra)."""
from datetime import date
from sqlmodel import Field, SQLModel
from typing import Optional

from app.base.auditoria import AuditMixin
from app.base.mixins_financieros import MixinDocumentoFinanciero

class BaseDocumento(MixinDocumentoFinanciero, AuditMixin, SQLModel):
    """
    Clase base abstracta para documentos financieros.
    Centraliza campos comunes y lógica compartida entre Cotizaciones y Ordenes de Compra.
    """
    # Campos comunes de negocio
    fecha_emision: date = Field(default_factory=date.today)
    estado: str = Field(index=True)
    
    # Datos de pago
    metodo_pago: str = Field(default="POR_DEFINIR", description="Método de pago SAT")
    forma_pago: str = Field(default="99", description="Forma de pago SAT")
    
    # Notas
    notas: Optional[str] = Field(default=None, description="Notas públicas/comerciales")
    notas_privadas: Optional[str] = Field(default=None, description="Notas internas")
    
    # Folio (aunque la estrategia de generación puede variar, el campo existe en ambos)
    folio: str = Field(index=True, unique=True)

    def actualizar_totales(self, detalles: list):
        """Wrapper para calcular totales usando el mixin."""
        # Se puede sobreescribir si se requiere lógica extra antes/después
        self.calcular_totales(detalles)
