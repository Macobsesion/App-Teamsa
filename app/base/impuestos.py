"""
Estrategias de Impuestos (Strategy Pattern).
Permite calcular impuestos de manera polimórfica según la región o régimen fiscal.
"""
from typing import Protocol
from decimal import Decimal

class CalculadoraImpuestos(Protocol):
    """Interfaz para estrategias de cálculo de impuestos."""
    def calcular(self, base_imponible: Decimal) -> Decimal:
        """Calcula el monto del impuesto sobre la base dada."""
        ...

class ImpuestoEstandarMX:
    """IVA Estándar México (16%)."""
    def calcular(self, base_imponible: Decimal) -> Decimal:
        return base_imponible * Decimal("0.16")

class ImpuestoFronteraMX:
    """IVA Frontera México (8%)."""
    def calcular(self, base_imponible: Decimal) -> Decimal:
        return base_imponible * Decimal("0.08")

class ImpuestoTasaCero:
    """Tasa Cero o Exento (0%)."""
    def calcular(self, base_imponible: Decimal) -> Decimal:
        return Decimal("0.00")
