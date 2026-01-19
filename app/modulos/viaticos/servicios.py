"""
Servicios de dominio para el módulo de viáticos.
Lógica de negocio pura para cálculos de fechas y montos.
"""
from datetime import date
from decimal import Decimal
from typing import List, Protocol


class ItemGasto(Protocol):
    """Protocolo para objetos que tienen importe y categoría."""
    importe: Decimal
    categoria: str


class ServicioCalculadoraViatico:
    """
    Servicio puro para cálculos de viáticos.
    """

    @staticmethod
    def calcular_dias(fecha_inicio: date, fecha_fin: date) -> int:
        """
        Calcula la duración del viático en días.
        Regla: (fin - inicio) + 1 para incluir ambos días.
        """
        if fecha_fin < fecha_inicio:
            return 0
        return (fecha_fin - fecha_inicio).days + 1

    @staticmethod
    def calcular_totales(gastos: List[ItemGasto]) -> dict[str, Decimal]:
        """
        Calcula los totales agrupados por categoría.
        """
        # Inicializar totales
        totales = {
            "transporte": Decimal("0.00"),
            "alojamiento": Decimal("0.00"),
            "alimentos": Decimal("0.00"),
            "otros": Decimal("0.00"),
            "general": Decimal("0.00")
        }

        # Sumar por categoría
        for gasto in gastos:
            if gasto.categoria in totales:
                totales[gasto.categoria] += gasto.importe
            else:
                # Si hay categorías no mapeadas, se podrían sumar a 'otros' o ignorar
                # Asumimos que validación de categoría ocurre antes
                pass
                
        # Calcular total general
        totales["general"] = (
            totales["transporte"] + 
            totales["alojamiento"] + 
            totales["alimentos"] + 
            totales["otros"]
        )

        return totales
