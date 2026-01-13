"""
Usuarios: API JSON + UI HTMX con generador genérico.

Se mantiene el DescriptorCRUD y se sustituye la UI manual por el builder
`construir_enrutador_ui` para evitar duplicación entre módulos.
"""
from fastapi import Depends  # type: ignore

from app.base.descriptor_crud import DescriptorCRUD
from app.base.ui_crud import DescriptorUI, construir_enrutador_ui
from app.modulos.usuarios.usuarios_esquemas import (
    UsuarioCreate,
    UsuarioIdentity,
    UsuarioRead,
    UsuarioUpdatePartial,
)
from app.modulos.usuarios.usuarios_repositorio import RepositorioUsuario
from app.nucleo.cls_autenticacion import obtener_gestor_autenticacion
from app.base.mapas import area_por_rol
from app.rutas.dependencias import dp_obtener_sesion_db, dp_usuario_actual, exigir_roles


def _hashear_contrasena(contrasena: str) -> str:
    return obtener_gestor_autenticacion().obtener_hash_contrasena(contrasena)



def _extra_creacion(payload: UsuarioCreate, actor: UsuarioIdentity) -> dict[str, object]:
    # Genera campos adicionales listos para el modelo (sin lógica en el repositorio)
    rol = payload.rol or 'funcionario'
    extras: dict[str, object] = {
        'rol': rol,
        'contrasena': _hashear_contrasena(payload.contrasena),
        'creado_por': actor.usuario,
        'modificado_por': actor.usuario,
    }
    return extras


def _extra_actualizacion(_payload: UsuarioUpdatePartial, actor: UsuarioIdentity) -> dict[str, object]:
    # Auditoría estándar desde el propio router
    extras: dict[str, object] = {'modificado_por': actor.usuario}
    # Si llega una contraseña no vacía, hashearla
    try:
        nueva_pass = getattr(_payload, 'contrasena', None)
        if nueva_pass:
            extras['contrasena'] = _hashear_contrasena(nueva_pass)
    except Exception:
        pass
    return extras


def _validar_unicidad(repo: RepositorioUsuario, payload: UsuarioCreate) -> str | None:
    if repo.obtener_por_username(username=payload.usuario):
        return "El usuario ya existe"
    return None


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
    campos_editables={"nombres", "correo", "area", "rol", "contrasena"},
    campos_creacion_extra=_extra_creacion,
    campos_actualizacion_extra=_extra_actualizacion,
    validar_unicidad=_validar_unicidad,
    filtros_permitidos={"rol", "area"},
    campo_busqueda="nombres",
    topic="usuarios",
    mensajes={
        'validacionNombres': 'El campo nombres no puede estar vacío',
        'validacionCorreo': 'El campo correo no puede estar vacío',
        'validacionArea': 'Selecciona un área',
        'validacionUsuario': 'El campo usuario no puede estar vacío',
        'validacionContrasena': 'La contraseña es requerida',
        'validacionConfirmacion': 'Las contraseñas deben coincidir',
        'correoInvalido': 'Correo no válido',
        'confirmacionCoincide': 'Las contraseñas coinciden',
        'confirmacionNoCoincide': 'Las contraseñas no coinciden',
    },
    columnas_incluir=[
        'usuario',
        'nombres',
        'rol',
        'correo',
        'area',
        'id',
        'fecha_creacion',
        'fecha_modificacion',
        'creado_por',
        'modificado_por',
    ],
    selectores={
        'tablaId': 'tablaUsuarios',
        'modalId': 'editModal',
        'modalTituloId': 'editModalLabel',
        'modalConfirmGroupId': 'grupoConfirmacion',
        'modalFeedbackId': 'modalPassFeedback',
        'botones': {
            'guardar': 'btnGuardar',
            'agregar': 'btnAgregar',
        },
        # IDs de campos se definen en form para permitir auto-render del modal
    },
    form=[
        {'name': 'id', 'label': 'ID', 'type': 'hidden', 'id': 'modalUsuarioId'},
        {'name': 'usuario', 'label': 'Usuario', 'type': 'text', 'id': 'modalUsuario', 'required': True, 'createOnly': True},
        {'name': 'nombres', 'label': 'Nombres', 'type': 'text', 'id': 'modalNombres', 'required': True},
        {'name': 'rol', 'label': 'Rol', 'type': 'select', 'id': 'modalRol', 'options': [
            {'value': 'admin', 'label': 'Admin'},
            {'value': 'funcionario', 'label': 'Funcionario'},
            {'value': 'productor', 'label': 'Productor'},
            {'value': 'conductor', 'label': 'Conductor'},
            {'value': 'camarografo', 'label': 'Camarógrafo'}
        ], 'required': True},
        {'name': 'correo', 'label': 'Correo', 'type': 'email', 'id': 'modalCorreo', 'required': True},
        {'name': 'contrasena', 'label': 'Contraseña', 'type': 'password', 'id': 'modalPassword', 'required': True, 'createOnly': True},
        {'name': 'confirmarContrasena', 'label': 'Confirma la contraseña', 'type': 'password', 'id': 'modalPasswordConfirmacion', 'createOnly': True, 'confirmWith': 'contrasena'},
    ],
)

api_router = descriptor.to_api_router(
    obtener_sesion=dp_obtener_sesion_db,
    list_dependencies=[Depends(dp_usuario_actual)],
    write_dependency=exigir_roles("admin"),
)
from fastapi import APIRouter


def _validar_form_creacion(datos: dict[str, object]) -> str | None:
    # Confirmación de contraseña en el formulario de creación
    if datos.get("contrasena") != datos.get("confirmarContrasena"):
        return "Las contraseñas no coinciden"
    return None


ui_router = construir_enrutador_ui(
    prefix="/ui/usuarios",
    repo_factory=RepositorioUsuario,
    schema_create=UsuarioCreate,
    schema_update=UsuarioUpdatePartial,
    hooks=descriptor.build_hooks(),
    obtener_sesion=dp_obtener_sesion_db,
    list_dependencies=[Depends(dp_usuario_actual)],
    write_dependency=exigir_roles("admin"),
    ui=DescriptorUI(
        tpl_filas="ui/usuarios/_filas.html",
        tpl_form="ui/usuarios/_form.html",
    ),
    label=descriptor.label,
    validar_form_creacion=_validar_form_creacion,
    actor_dependency=dp_usuario_actual,
    columnas=descriptor.frontend_config()["columnas"],
    campo_busqueda=descriptor.campo_busqueda,
)

# Router combinado (API + UI)
router = APIRouter()
router.include_router(api_router)
router.include_router(ui_router)
