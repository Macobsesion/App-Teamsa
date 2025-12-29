"""Router y descriptor CRUD para servicios."""
from fastapi import APIRouter, Depends  # type: ignore
from sqlmodel import Session  # type: ignore

from app.base.descriptor_crud import DescriptorCRUD
from app.base.ui_crud import DescriptorUI, construir_enrutador_ui
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import exigir_roles, dp_usuario_actual
from app.modulos.servicios.servicios_esquemas import ServicioRead, ServicioCreate, ServicioUpdate
from app.modulos.servicios.servicios_repositorio import RepositorioServicio
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity


def _validar_unicidad(repo: RepositorioServicio, payload: ServicioCreate) -> str | None:
    """Valida que no exista un servicio con la misma clave."""
    if repo.obtener_por_clave(payload.clave):
        return f"Ya existe un servicio con la clave '{payload.clave}'"
    return None


descriptor = DescriptorCRUD[RepositorioServicio, ServicioCreate, ServicioUpdate, ServicioRead, UsuarioIdentity](
    label="Servicios",
    base_url="/api/servicios",
    repo_factory=RepositorioServicio,  # Clase directa - auditoría automática
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

router_api = descriptor.to_api_router(
    obtener_sesion=obtener_sesion_bd,
    write_dependency=exigir_roles("admin"),
)

router_ui = construir_enrutador_ui(
    prefix="/ui/servicios",
    repo_factory=RepositorioServicio,
    schema_create=ServicioCreate,
    schema_update=ServicioUpdate,
    hooks=descriptor.build_hooks(),
    obtener_sesion=obtener_sesion_bd,
    list_dependencies=[Depends(dp_usuario_actual)],
    write_dependency=exigir_roles("admin"),
    ui=DescriptorUI(
        tpl_filas="ui/servicios/_filas.html",
        tpl_form="ui/servicios/_form.html",
    ),
    label=descriptor.label,
    actor_dependency=dp_usuario_actual,
    columnas=descriptor.frontend_config().get("columnas"),
    campo_busqueda=descriptor.campo_busqueda,
)

@router_api.get("/select", response_model=list[dict])
def obtener_servicios_para_select(
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Devuelve lista de servicios activos para usar en selects/dropdowns."""
    repo = RepositorioServicio(db)
    servicios = repo.listar()
    
    return [
        {
            "id": s.id,
            "clave": s.clave,
            "descripcion": s.descripcion,
            "codigo_sat": s.codigo_sat or "",
            "unidad": s.unidad or "",
            "precio_base": float(s.precio_base) if s.precio_base else 0.0,
            "area": s.area or "",  # Cambiado de 'tipo' a 'area'
            "activo": s.activo
        }
        for s in servicios
        if s.activo
    ]

router = APIRouter()
router.include_router(router_api)
router.include_router(router_ui)
