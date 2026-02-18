"""
Usuarios: API JSON + UI HTMX usando factory pattern.

Migrado al factory pattern para reducir duplicación y simplificar mantenimiento.
"""
from typing import Any

from app.base.descriptor_crud import DescriptorCRUD
from app.base.factory_modulo import crear_modulo_crud
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import dp_usuario_actual, exigir_roles
from app.modulos.usuarios.usuarios_esquemas import (
    UsuarioCreate,
    UsuarioIdentity,
    UsuarioRead,
    UsuarioUpdatePartial,
)
from app.modulos.usuarios.usuarios_repositorio import RepositorioUsuario

def _validar_unicidad(repo: RepositorioUsuario, payload: UsuarioCreate) -> str | None:
    """Valida que el usuario no exista."""
    # Usar el método genérico del repositorio base
    if repo.obtener_por_campo("usuario", payload.usuario):
        return "El usuario ya existe"
    return None


def _validar_form_creacion(datos: dict[str, object]) -> str | None:
    """Validación específica de formulario: confirmación de contraseña."""
    if datos.get("contrasena") != datos.get("confirmarContrasena"):
        return "Las contraseñas no coinciden"
    return None


# ---------- Descriptor ----------
descriptor = DescriptorCRUD[
    RepositorioUsuario,
    UsuarioCreate,
    UsuarioUpdatePartial,
    UsuarioRead,
    UsuarioIdentity,
](
    label="Usuarios",
    base_url="/api/usuarios",
    repo_factory=RepositorioUsuario,
    schema_read=UsuarioRead,
    schema_create=UsuarioCreate,
    schema_update=UsuarioUpdatePartial,
    campos_editables={
        "nombres", "rol", "correo", "contrasena", "area"
    },
    columnas_incluir=["usuario", "rol", "correo", "area"],
    columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion", "contrasena"},
    validar_unicidad=_validar_unicidad,
    filtros_permitidos={"rol", "area"},
    campo_busqueda="nombres",
)


# ---------- Router Combinado usando Factory ----------
router = crear_modulo_crud(
    descriptor=descriptor,
    obtener_sesion=obtener_sesion_bd,
    actor_dependency=dp_usuario_actual,
    write_dependency=exigir_roles("admin"),
    tpl_filas="ui/usuarios/_filas.html",
    tpl_form="ui/usuarios/_form.html",
    validar_form_creacion=_validar_form_creacion,
)
