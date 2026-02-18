"""Router y descriptor CRUD para proveedores."""
from app.base.descriptor_crud import DescriptorCRUD
from app.base.factory_modulo import crear_modulo_crud
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import exigir_roles, dp_usuario_actual
from app.modulos.proveedores.proveedores_esquemas import ProveedorRead, ProveedorCreate, ProveedorUpdate
from app.modulos.proveedores.proveedores_repositorio import RepositorioProveedor
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity


def _validar_unicidad(repo: RepositorioProveedor, payload: ProveedorCreate) -> str | None:
    """Valida que no exista un proveedor con el mismo nombre."""
    if repo.obtener_por_campo("nombre", payload.nombre):
        return f"Ya existe un proveedor con el nombre '{payload.nombre}'"
    return None


# ---------- Descriptor ----------
descriptor = DescriptorCRUD[RepositorioProveedor, ProveedorCreate, ProveedorUpdate, ProveedorRead, UsuarioIdentity](
    label="Proveedores",
    base_url="/api/proveedores",
    repo_factory=RepositorioProveedor,  # Clase directa - auditoría automática
    schema_read=ProveedorRead,
    schema_create=ProveedorCreate,
    schema_update=ProveedorUpdate,
    campos_editables={
        "nombre", "rfc", "razon_social", "contacto", "email",
        "telefono", "direccion", "ciudad", "cp",
        "categoria", "activo", "notas"
    },
    validar_unicidad=_validar_unicidad,
    filtros_permitidos={"activo", "categoria"},
    campo_busqueda="nombre",
    columnas_incluir=["nombre", "rfc", "contacto", "categoria", "activo"],
    columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
)



# ---------- Router Combinado usando Factory ----------
router = crear_modulo_crud(
    descriptor=descriptor,
    obtener_sesion=obtener_sesion_bd,
    actor_dependency=dp_usuario_actual,
    write_dependency=exigir_roles("admin"),
    tpl_filas="ui/proveedores/_filas.html",
    tpl_form="ui/proveedores/_form.html",
    include_select_endpoint=True,
    select_fields=["id", "nombre", "rfc", "categoria", "activo"],
)

