"""Router y descriptor CRUD para clientes."""
from fastapi import APIRouter, Depends  # type: ignore
from sqlmodel import Session  # type: ignore

from app.base.descriptor_crud import DescriptorCRUD
from app.base.ui_crud import DescriptorUI, construir_enrutador_ui
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import exigir_roles, dp_usuario_actual
from app.modulos.clientes.clientes_esquemas import ClienteRead, ClienteCreate, ClienteUpdate
from app.modulos.clientes.clientes_repositorio import RepositorioCliente
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity


def _validar_unicidad(repo: RepositorioCliente, payload: ClienteCreate) -> str | None:
    """Valida que no exista un cliente con el mismo nombre."""
    if repo.obtener_por_nombre(payload.nombre):
        return f"Ya existe un cliente con el nombre '{payload.nombre}'"
    return None


descriptor = DescriptorCRUD[RepositorioCliente, ClienteCreate, ClienteUpdate, ClienteRead, UsuarioIdentity](
    label="Clientes",
    base_url="/api/clientes",
    repo_factory=RepositorioCliente,  # Clase directa - auditoría automática
    schema_read=ClienteRead,
    schema_create=ClienteCreate,
    schema_update=ClienteUpdate,
    campos_editables={
        "nombre", "rfc", "razon_social", "contacto", "email",
        "telefono", "direccion", "ciudad", "cp",
        "activo", "notas"
    },
    validar_unicidad=_validar_unicidad,
    filtros_permitidos={"activo"},
    campo_busqueda="nombre",
    columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
)

router_api = descriptor.to_api_router(
    obtener_sesion=obtener_sesion_bd,
    write_dependency=exigir_roles("admin"),
)

router_ui = construir_enrutador_ui(
    prefix="/ui/clientes",
    repo_factory=RepositorioCliente,
    schema_create=ClienteCreate,
    schema_update=ClienteUpdate,
    hooks=descriptor.build_hooks(),
    obtener_sesion=obtener_sesion_bd,
    list_dependencies=[Depends(dp_usuario_actual)],
    write_dependency=exigir_roles("admin"),
    ui=DescriptorUI(
        tpl_filas="ui/clientes/_filas.html",
        tpl_form="ui/clientes/_form.html",
    ),
    label=descriptor.label,
    actor_dependency=dp_usuario_actual,
    columnas=descriptor.frontend_config().get("columnas"),
    campo_busqueda=descriptor.campo_busqueda,
)

@router_api.get("/select", response_model=list[dict])
def obtener_clientes_para_select(
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Devuelve lista de clientes activos para usar en selects/dropdowns."""
    repo = RepositorioCliente(db)
    clientes = repo.listar()
    
    return [
        {
            "id": c.id,
            "nombre": c.nombre,
            "rfc": c.rfc or "",
            "email": c.email or "",
            "activo": c.activo
        }
        for c in clientes
        if c.activo  # Solo clientes activos
    ]

router = APIRouter()
router.include_router(router_api)
router.include_router(router_ui)
