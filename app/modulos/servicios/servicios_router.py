"""Router y descriptor CRUD para servicios."""
from app.base.descriptor_crud import DescriptorCRUD
from app.base.factory_modulo import crear_modulo_crud
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import dp_usuario_actual
from app.rutas.permisos import para_modulo
from app.modulos.servicios.servicios_esquemas import ServicioRead, ServicioCreate, ServicioUpdate
from app.modulos.servicios.servicios_repositorio import RepositorioServicio
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity


def _validar_unicidad(repo: RepositorioServicio, payload: ServicioCreate) -> str | None:
    """Valida que no exista un servicio con la misma clave."""
    if repo.obtener_por_campo("clave", payload.clave):
        return f"Ya existe un servicio con la clave '{payload.clave}'"
    return None


# ---------- Descriptor ----------
descriptor = DescriptorCRUD[RepositorioServicio, ServicioCreate, ServicioUpdate, ServicioRead, UsuarioIdentity](
    label="Servicios",
    base_url="/api/servicios",
    repo_factory=RepositorioServicio,
    schema_read=ServicioRead,
    schema_create=ServicioCreate,
    schema_update=ServicioUpdate,
    campos_editables={
        "codigo_sat", "codigo_unidad", "clave", "descripcion",
        "tipo", "precio_base", "unidad", "activo", "notas"
    },
    validar_unicidad=_validar_unicidad,
    filtros_permitidos={"activo", "tipo"},
    campo_busqueda="clave",
    columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
)


# ---------- Router Combinado usando Factory ----------
router = crear_modulo_crud(
    descriptor=descriptor,
    obtener_sesion=obtener_sesion_bd,
    actor_dependency=dp_usuario_actual,
    write_dependency=para_modulo("servicios"),
    tpl_filas="ui/servicios/_filas.html",
    tpl_form="ui/servicios/_form.html",
    include_select_endpoint=True,
    select_fields=["id", "clave", "descripcion", "codigo_sat", "unidad", "precio_base", "activo"],
)



