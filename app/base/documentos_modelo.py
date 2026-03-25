"""Modelo base para Documentos Financieros (Cotizaciones, Órdenes de Compra)."""
from datetime import date
from sqlmodel import Field, SQLModel
from typing import Optional, Any

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

    # ---- PROPIEDADES DE ESTADO ABSTRACTAS (POLIMORFISMO) ----
    @property
    def estado_enum(self) -> Any:
        """Devuelve el estado como objeto Enum correspondiente (a implementar por la subclase)."""
        raise NotImplementedError("Subclases deben implementar estado_enum")

    @property
    def es_editable(self) -> bool:
        """Delega la verificación al enum subyacente de forma polimórfica."""
        if hasattr(self.estado_enum, "es_editable"):
            return self.estado_enum.es_editable
        return False

    @property
    def es_cancelable(self) -> bool:
        """Delega la verificación al enum subyacente de forma polimórfica."""
        if hasattr(self.estado_enum, "es_cancelable"):
            return self.estado_enum.es_cancelable
        return False

    def actualizar_notas_privadas(self, notas: Optional[str], usuario_id: str) -> None:
        """Encapsula la mutación de notas privadas con rastro de auditoría."""
        from datetime import datetime
        self.notas_privadas = notas
        self.modificado_por = usuario_id
        self.fecha_modificacion = datetime.now()
