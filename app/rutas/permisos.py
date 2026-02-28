"""
Tabla central de permisos por módulo.

Para cambiar quién puede acceder a un módulo, sólo edita PERMISOS_MODULOS.
Todos los routers importan `para_modulo(nombre)` en lugar de `exigir_roles(...)`.
"""
from app.rutas.dependencias import exigir_roles, dp_usuario_actual

# ── Tabla central: módulo → roles autorizados para escritura ─────────────────
# Keys: nombre del módulo (usar el mismo string en para_modulo()).
# Values: tupla de roles que pueden crear/editar/eliminar en ese módulo.
PERMISOS_MODULOS: dict[str, tuple[str, ...]] = {
    "usuarios":               ("admin",),
    "clientes":               ("admin",),
    "servicios":              ("admin",),
    "proveedores":            ("admin", "funcionario"),
    "cotizaciones":           ("admin",),
    "ordenes":                ("admin",),
    "ordenes_compra":         ("admin", "tecnico", "funcionario"),
    "servicios_proveedores":  ("admin", "tecnico", "funcionario"),
}


def para_modulo(modulo: str):
    """
    Retorna la dependencia FastAPI de autorización para el módulo dado.

    Uso en routers:
        write_dependency=para_modulo("ordenes_compra")
        actor: UsuarioIdentity = Depends(para_modulo("cotizaciones"))

    Lanza ValueError si el módulo no está registrado en PERMISOS_MODULOS,
    lo que evita errores silenciosos por typos.
    """
    roles = PERMISOS_MODULOS.get(modulo)
    if not roles:
        raise ValueError(
            f"Módulo '{modulo}' no tiene permisos definidos en PERMISOS_MODULOS. "
            f"Módulos válidos: {sorted(PERMISOS_MODULOS)}"
        )
    return exigir_roles(*roles)



# ── Mapa ruta HTML → módulo (para visibilidad del navbar) ────────────────────
# Clave: prefijo de URL que aparece en el navbar.
# Valor: nombre de módulo en PERMISOS_MODULOS.
RUTAS_MODULO: dict[str, str] = {
    "/usuarios":              "usuarios",
    "/clientes":              "clientes",
    "/servicios":             "servicios",
    "/proveedores":           "proveedores",
    "/cotizaciones":          "cotizaciones",
    "/ordenes":               "ordenes",
    "/ordenes-compra":        "ordenes_compra",
    "/servicios-proveedores": "servicios_proveedores",
}


def puede_ver(ruta: str, rol: str) -> bool:
    """Retorna True si el rol dado tiene permiso para ver la ruta.

    Usada como función global en los templates Jinja para mostrar/ocultar
    elementos del navbar según el rol del usuario autenticado.
    """
    modulo = RUTAS_MODULO.get(ruta)
    if modulo is None:
        return True  # rutas no registradas son públicas por defecto
    roles_permitidos = PERMISOS_MODULOS.get(modulo, ())
    return rol.lower() in {r.lower() for r in roles_permitidos}


__all__ = ["para_modulo", "PERMISOS_MODULOS", "RUTAS_MODULO", "puede_ver"]
