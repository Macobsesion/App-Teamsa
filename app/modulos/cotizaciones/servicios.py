"""
Servicios de dominio para el módulo de cotizaciones.
Aquí reside la lógica de negocio pura, separada de la persistencia de datos.
"""
from decimal import Decimal
from typing import List, Protocol

from app.base.constantes import IVA_PORCENTAJE


class ItemCotizable(Protocol):
    """Protocolo que define qué necesita tener un objeto para ser calculado."""
    cantidad: Decimal
    precio_unitario: Decimal
    descuento_porcentaje: Decimal


class ServicioCalculadoraCotizacion:
    """
    Servicio de dominio puro para realizar cálculos financieros de cotizaciones.
    
    No depende de la base de datos ni de modelos específicos, solo de datos
    que cumplan con el protocolo ItemCotizable (o duck typing).
    """

    @staticmethod
    def calcular_totales(conceptos: List[ItemCotizable]) -> dict[str, Decimal]:
        """
        Calcula los totales financieros de una lista de conceptos.
        
        Reglas de negocio:
        1. Subtotal = Suma de (cantidad * precio)
        2. Descuento = Suma de descuentos individuales
        3. IVA = 16% sobre (Subtotal - Descuento)
        4. Total = Base + IVA
        """
        subtotal = Decimal("0.00")
        descuento_global = Decimal("0.00")

        for concepto in conceptos:
            # Calcular subtotal línea
            subtotal_linea = concepto.cantidad * concepto.precio_unitario
            subtotal += subtotal_linea

            # Calcular descuento línea
            if concepto.descuento_porcentaje > 0:
                descuento_monto = subtotal_linea * (concepto.descuento_porcentaje / Decimal("100"))
                descuento_global += descuento_monto

        # Base imponible
        base_iva = subtotal - descuento_global

        # Calcular IVA
        iva = base_iva * Decimal(str(IVA_PORCENTAJE))

        # Total final
        total = base_iva + iva

        return {
            "subtotal": subtotal,
            "descuento_global": descuento_global,
            "iva": iva,
            "total": total
        }

    @staticmethod
    def extraer_numero_base(numero: str) -> str:
        """
        Extrae el número base sin letra de versión (e.g. COT-00001-B -> COT-00001).
        """
        partes = numero.split('-')
        if len(partes) == 2:
            return numero
        elif len(partes) >= 3:
            return f"{partes[0]}-{partes[1]}"
        return numero

    @staticmethod
    def calcular_siguiente_letra(letras_usadas: List[str | None]) -> str:
        """
        Calcula la siguiente letra de versión basándose en las ya usadas.
        Secuencia: B, C, ..., Z, AA, AB...
        """
        # Filtrar None y ordenar
        letras = [l for l in letras_usadas if l is not None]
        
        # Si no hay letras, empezar con B
        if not letras:
            return "B"
        
        # Encontrar la última letra
        ultima = max(letras)
        
        # Caso 1: Letra simple (B-Z)
        if len(ultima) == 1:
            if ultima == "Z":
                return "AA"
            else:
                return chr(ord(ultima) + 1)
        
        # Caso 2: Doble letra (AA, AB...)
        elif len(ultima) == 2:
            primera, segunda = ultima[0], ultima[1]
            if segunda == "Z":
                if primera == "Z":
                    return "AAA"
                else:
                    return chr(ord(primera) + 1) + "A"
            else:
                return primera + chr(ord(segunda) + 1)
        
        return "B"  # Fallback seguro
