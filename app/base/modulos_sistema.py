"""
ModuloSistema — Fuente de verdad para módulos del sistema.

Centraliza los nombres de módulos para que el RBAC, las rutas HTML y 
cualquier servicio de aplicación que cruce módulos use los mismos valores.
"""
from enum import Enum


class ModuloSistema(str, Enum):
    """Módulos disponibles en el sistema TEAMSA."""
    USUARIOS = "usuarios"
    CLIENTES = "clientes"
    PROVEEDORES = "proveedores"
    SERVICIOS = "servicios"
    SERVICIOS_PROVEEDORES = "servicios_proveedores"
    COTIZACIONES = "cotizaciones"
    ORDENES = "ordenes_trabajo"
    ORDENES_COMPRA = "ordenes_compra"
    VIATICOS = "viaticos"
    AUDITORIA = "auditoria"

    @property
    def label(self) -> str:
        """Nombre legible para mostrar en UI / logs."""
        return self.value.replace("_", " ").title()
