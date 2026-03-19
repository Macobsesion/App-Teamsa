"""Mapas y utilidades simples de conversión/derivación compartidos.

Mantener KISS: funciones puras, nombres autoexplicativos.
"""
from __future__ import annotations


# Mapeo de roles internos a áreas organizacionales
# Centralizado aquí para facilitar cambios sin buscar en todo el código
AREA_POR_ROL: dict[str, str] = {
    'admin': 'TI',
    'funcionario': 'Administración',
    'productor': 'Producción',
    'conductor': 'Producción',
    'camarografo': 'Técnica',
}


def area_por_rol(rol: str) -> str:
    return AREA_POR_ROL.get(rol, 'Administración')


__all__ = ["area_por_rol", "AREA_POR_ROL"]
