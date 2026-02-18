"""Router y descriptor CRUD para clientes."""
from app.base.descriptor_crud import DescriptorCRUD
from app.base.factory_modulo import crear_modulo_crud
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import exigir_roles, dp_usuario_actual
from app.modulos.clientes.clientes_esquemas import ClienteRead, ClienteCreate, ClienteUpdate
from app.modulos.clientes.clientes_repositorio import RepositorioCliente
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity


def _validar_unicidad(repo: RepositorioCliente, payload: ClienteCreate) -> str | None:
    """Valida que no exista un cliente con el mismo nombre."""
    if repo.obtener_por_campo("nombre", payload.nombre):
        return f"Ya existe un cliente con el nombre '{payload.nombre}'"
    return None


# ---------- Descriptor ----------
descriptor = DescriptorCRUD[RepositorioCliente, ClienteCreate, ClienteUpdate, ClienteRead, UsuarioIdentity](
    label="Clientes",
    base_url="/api/clientes",
    repo_factory=RepositorioCliente,
    schema_read=ClienteRead,
    schema_create=ClienteCreate,
    schema_update=ClienteUpdate,
    campos_editables={
        "nombre", "rfc", "razon_social", "contacto", "email",
        "telefono", "direccion", "ciudad", "cp", "activo", "notas"
    },
    validar_unicidad=_validar_unicidad,
    filtros_permitidos={"activo"},
    campo_busqueda="nombre",
    columnas_incluir=["nombre", "rfc", "contacto", "email", "activo"],
    columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
)


# ---------- Router Combinado usando Factory ----------
router = crear_modulo_crud(
    descriptor=descriptor,
    obtener_sesion=obtener_sesion_bd,
    actor_dependency=dp_usuario_actual,
    write_dependency=exigir_roles("admin"),
    tpl_filas="ui/clientes/_filas.html",
    tpl_form="ui/clientes/_form.html",
    include_select_endpoint=True,
    select_fields=["id", "nombre", "rfc", "email", "activo"],
)

