"""Router y descriptor CRUD para proveedores."""
from fastapi import APIRouter, Depends  # type: ignore
from sqlmodel import Session  # type: ignore

from app.base.descriptor_crud import DescriptorCRUD
from app.base.ui_crud import DescriptorUI, construir_enrutador_ui
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import exigir_roles, dp_usuario_actual
from app.modulos.proveedores.proveedores_esquemas import ProveedorRead, ProveedorCreate, ProveedorUpdate
from app.modulos.proveedores.proveedores_repositorio import RepositorioProveedor
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity


def _validar_unicidad(repo: RepositorioProveedor, payload: ProveedorCreate) -> str | None:
    """Valida que no exista un proveedor con el mismo nombre."""
    if repo.obtener_por_nombre(payload.nombre):
        return f"Ya existe un proveedor con el nombre '{payload.nombre}'"
    return None


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
    columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
)

router_api = descriptor.to_api_router(
    obtener_sesion=obtener_sesion_bd,
    write_dependency=exigir_roles("admin"),
)

router_ui = construir_enrutador_ui(
    prefix="/ui/proveedores",
    repo_factory=RepositorioProveedor,
    schema_create=ProveedorCreate,
    schema_update=ProveedorUpdate,
    hooks=descriptor.build_hooks(),
    obtener_sesion=obtener_sesion_bd,
    list_dependencies=[Depends(dp_usuario_actual)],
    write_dependency=exigir_roles("admin"),
    ui=DescriptorUI(
        tpl_filas="ui/proveedores/_filas.html",
        tpl_form="ui/proveedores/_form.html",
    ),
    label=descriptor.label,
    actor_dependency=dp_usuario_actual,
    columnas=descriptor.frontend_config().get("columnas"),
    campo_busqueda=descriptor.campo_busqueda,
)

router = APIRouter()
router.include_router(router_api)
router.include_router(router_ui)
