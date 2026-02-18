"""
Mixins Financieros.
Proveen campos y lógica estándar para documentos transaccionales (Cotizaciones, Ordenes de Compra, Facturas).
"""
from decimal import Decimal
from typing import List, Protocol, TYPE_CHECKING
from sqlmodel import Field

if TYPE_CHECKING:
    from app.base.impuestos import CalculadoraImpuestos

class MixinDetalleFinanciero:
    """
    Mixin para items/detalles de una transacción (ej. Concepto de Cotización).
    Provee campos: cantidad, precio_unitario, descuento_porcentaje, importe.
    """
    cantidad: Decimal = Field(default=Decimal("1.00"), decimal_places=2)
    precio_unitario: Decimal = Field(decimal_places=2, description="Precio por unidad")
    descuento_porcentaje: Decimal = Field(default=Decimal("0.00"), decimal_places=2, description="% descuento (0-100)")
    importe: Decimal = Field(decimal_places=2, description="Total de línea: (cant*precio) - desc")

    def calcular_importe(self) -> None:
        """Calcula el importe de la línea basándose en sus valores."""
        subtotal = self.cantidad * self.precio_unitario
        descuento = subtotal * (self.descuento_porcentaje / Decimal("100"))
        self.importe = subtotal - descuento


# Protocolo para duck-typing en el cálculo de totales
class ItemFinanciero(Protocol):
    importe: Decimal
    descuento_porcentaje: Decimal
    cantidad: Decimal
    precio_unitario: Decimal


class MixinDocumentoFinanciero:
    """
    Mixin para cabeceras de documentos financieros.
    Provee campos: subtotal, descuento_global, iva, total.
    """
    subtotal: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    descuento_global: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    iva: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    total: Decimal = Field(default=Decimal("0.00"), decimal_places=2)


    def calcular_totales(
        self, 
        detalles: List[ItemFinanciero],
        estrategia_impuestos: "CalculadoraImpuestos | None" = None
    ) -> None:
        """
        Recalcula subtotal, descuento, iva y total sumando los detalles.
        Permite inyectar estrategia de impuestos (Default: IVA 16%).
        """
        # Evitar import circular o necesitar importar en módulo si no se usa
        if estrategia_impuestos is None:
            from app.base.impuestos import ImpuestoEstandarMX
            estrategia_impuestos = ImpuestoEstandarMX()

        # 1. Sumar importes brutos (antes de descuento)
        acum_subtotal = Decimal("0.00")
        acum_descuento = Decimal("0.00")
        
        for d in detalles:
            linea_bruto = d.cantidad * d.precio_unitario
            linea_desc = linea_bruto * (d.descuento_porcentaje / Decimal("100"))
            
            acum_subtotal += linea_bruto
            acum_descuento += linea_desc
            
        base_imponible = acum_subtotal - acum_descuento
        
        # POLIMORFISMO: Delegar el cálculo del impuesto a la estrategia
        iva_calculado = estrategia_impuestos.calcular(base_imponible)
        
        self.subtotal = acum_subtotal
        self.descuento_global = acum_descuento
        self.iva = iva_calculado
        self.total = base_imponible + iva_calculado
