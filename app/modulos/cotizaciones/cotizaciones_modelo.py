"""Modelos SQLModel para cotizaciones y conceptos."""
from datetime import date, datetime
from decimal import Decimal
from sqlmodel import Field, SQLModel, Relationship  # type: ignore
from typing import TYPE_CHECKING

from app.base.auditoria import AuditMixin

if TYPE_CHECKING:
    from app.modulos.clientes.clientes_modelo import Cliente


class Cotizacion(AuditMixin, SQLModel, table=True):
    """Cotización comercial con conceptos dinámicos."""
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Numeración única y secuencial
    numero: str = Field(unique=True, index=True, description="Número de cotización: COT-00001")
    
    # Relación con cliente
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    
    # Estado
    estado: str = Field(default="borrador", description="Estado: borrador, enviada, aceptada, rechazada, cobrado")
    
    # Importes calculados (suma de conceptos)
    subtotal: Decimal = Field(default=Decimal("0.00"), decimal_places=2, description="Suma de items (precio × cantidad)")
    descuento_global: Decimal = Field(default=Decimal("0.00"), decimal_places=2, description="Suma de descuentos de todos los conceptos")
    iva: Decimal = Field(default=Decimal("0.00"), decimal_places=2, description="16% sobre (subtotal - descuento)")
    total: Decimal = Field(default=Decimal("0.00"), decimal_places=2, description="subtotal - descuento + IVA")
    
    # Fechas
    fecha_emision: date = Field(default_factory=date.today)
    fecha_vigencia: date  # Se calcula: fecha_emision + 30 días
    
    # Método y forma de pago
    metodo_pago: str = Field(default="Por confirmar", description="Método de pago: Por confirmar, Transferencia SPEI, Efectivo, Cheque, Tarjeta")
    forma_pago: str = Field(default="99", description="Forma de pago SAT: 01=Efectivo, 03=Transferencia, 99=Por definir, etc.")
    
    # Información adicional
    notas: str | None = Field(default=None, description="Notas adicionales, origen de petición, observaciones")
    
    # Relationship (para cargar conceptos)
    # conceptos: list["ConceptoCotizacion"] = Relationship(back_populates="cotizacion")


class ConceptoCotizacion(SQLModel, table=True):
    """Concepto (item/línea) de una cotización."""
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Relación con cotización
    cotizacion_id: int = Field(foreign_key="cotizacion.id", index=True)
    
    # Relación con servicio (opcional, para trazabilidad)
    servicio_id: int | None = Field(default=None, foreign_key="servicio.id")
    
    # Datos del servicio copiados al momento de crear (snapshot)
    codigo_sat: str = Field(description="Código SAT del producto/servicio")
    descripcion: str = Field(description="Descripción del concepto")
    unidad: str = Field(description="Unidad de medida: pieza, hora, etc.")
    codigo_unidad: str = Field(default="H87", description="Código de unidad SAT")
    
    # Cantidad y precio
    cantidad: Decimal = Field(default=Decimal("1.00"), decimal_places=2)
    precio_unitario: Decimal = Field(decimal_places=2, description="Precio por unidad")
    
    # Descuento individual (por concepto)
    descuento_porcentaje: Decimal = Field(default=Decimal("0.00"), decimal_places=2, description="% de descuento en este concepto (0-100)")
    
    # Importe calculado: (cantidad × precio_unitario) - descuento
    importe: Decimal = Field(decimal_places=2, description="Total del concepto con descuento aplicado")
    
    # Relationships
    # cotizacion: "Cotizacion" = Relationship(back_populates="conceptos")
