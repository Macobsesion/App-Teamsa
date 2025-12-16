"""Mapas y utilidades simples de conversión/derivación compartidos.

Mantener KISS: funciones puras, nombres autoexplicativos.
"""
from __future__ import annotations


def area_por_rol(rol: str) -> str:
    mapping = {
        'admin': 'TI',
        'funcionario': 'Administracion',
        'productor': 'Produccion',
        'conductor': 'Produccion',
        'camarografo': 'técnica',
    }
    return mapping.get(rol, 'Administracion')

__all__ = ["area_por_rol"]

