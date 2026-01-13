"""Router y descriptor CRUD para órdenes de trabajo."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session
from app.rutas.dependencias import dp_usuario_actual, exigir_roles
from app.nucleo.base_datos import obtener_sesion_bd
from app.base.descriptor_crud import DescriptorCRUD
from app.base.ui_crud import DescriptorUI, construir_enrutador_ui
from app.base.permisos import ColumnaDef
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
from app.modulos.ordenes_trabajo.ordenes_trabajo_esquemas import (
    OrdenTrabajoCreate,
    OrdenTrabajoRead,
    OrdenTrabajoUpdate,
)
from app.modulos.ordenes_trabajo.ordenes_trabajo_repositorio import (
    RepositorioOrdenTrabajo,
    RepositorioConceptoOrdenTrabajo,
)
from fastapi.templating import Jinja2Templates

# Templates globales para vistas HTML
TEMPLATES = Jinja2Templates(directory="web/templates")


# Configuración descriptor CRUD
descriptor = DescriptorCRUD[RepositorioOrdenTrabajo, OrdenTrabajoCreate, OrdenTrabajoUpdate, OrdenTrabajoRead, UsuarioIdentity](
    label="Órdenes de Trabajo",
    base_url="/api/ordenes-trabajo",
    repo_factory=RepositorioOrdenTrabajo,
    schema_read=OrdenTrabajoRead,
    schema_create=OrdenTrabajoCreate,
    schema_update=OrdenTrabajoUpdate,
    campos_editables={
        "estado", "fecha_programada", "fecha_inicio", "fecha_completada",
        "tecnico_asignado_id", "notas", "observaciones_tecnicas"
    },
    filtros_permitidos={"estado", "cliente_id", "tecnico_asignado_id"},
    campo_busqueda="numero",
    columnas_excluir={
        "creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion",
        "cotizacion_id", "fecha_inicio", "fecha_completada", "notas", "observaciones_tecnicas"
    },
)

# Router API generado automáticamente
router_api = descriptor.to_api_router(
    obtener_sesion=obtener_sesion_bd,
    write_dependency=exigir_roles("admin"),
)

# Router UI generado automáticamente
router_ui = construir_enrutador_ui(
    prefix="/ui/ordenes-trabajo",
    repo_factory=RepositorioOrdenTrabajo,
    schema_create=OrdenTrabajoCreate,
    schema_update=OrdenTrabajoUpdate,
    hooks=descriptor.build_hooks(),
    obtener_sesion=obtener_sesion_bd,
    list_dependencies=[Depends(dp_usuario_actual)],
    write_dependency=exigir_roles("admin"),
    ui=DescriptorUI(
        tpl_filas="ui/ordenes_trabajo/_filas.html",
        tpl_form="ui/ordenes_trabajo/_form.html",
        titulo_singular="Orden de Trabajo",
        titulo_plural="Órdenes de Trabajo",
        
        columnas_definicion=[
            ColumnaDef(nombre="numero", label="Número", ancho="120px"),
            ColumnaDef(nombre="cliente", label="Cliente"),
            ColumnaDef(nombre="fecha", label="Fecha", formato="fecha"),
            ColumnaDef(
                nombre="estado",
                label="Estado",
                formato="badge",
                ancho="120px",
            ),
            ColumnaDef(
                nombre="acciones",
                label="Acciones",
                ordenable=False,
            ),
        ],
        usar_columnas_declarativas=True,
    ),
    label=descriptor.label,
    actor_dependency=dp_usuario_actual,
    columnas=descriptor.frontend_config().get("columnas"),
    campo_busqueda=descriptor.campo_busqueda,
)

# Router extra para endpoints especiales
router_extra_api = APIRouter(prefix="/api/ordenes-trabajo", tags=["Órdenes de Trabajo API"])
router_extra_ui = APIRouter(prefix="/ui/ordenes-trabajo", tags=["Órdenes de Trabajo UI"])


@router_extra_api.post("/crear-desde-cotizacion")
def crear_orden_desde_cotizacion(
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """
    Crea una orden de trabajo desde una cotización existente.
    
    Copia servicios SIN precios y notas públicas (NO privadas).
    """
    cotizacion_id = data.get("cotizacion_id")
    fecha_programada = data.get("fecha_programada")
    
    if not cotizacion_id:
        raise HTTPException(status_code=400, detail="cotizacion_id requerido")
    
    repo = RepositorioOrdenTrabajo(db)
    
    try:
        orden = repo.crear_desde_cotizacion(
            cotizacion_id=cotizacion_id,
            usuario=usuario.usuario,
            fecha_programada=fecha_programada,
        )
        
        return {
            "id": orden.id,
            "numero": orden.numero,
            "message": f"Orden de trabajo {orden.numero} creada exitosamente"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear orden: {str(e)}")


@router_extra_ui.get("/{orden_id}/detalle")
def ver_detalle_orden_trabajo(
    orden_id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual),
):
    """Vista de detalle de una orden de trabajo."""
    repo = RepositorioOrdenTrabajo(db)
    orden = repo.obtener(orden_id)
    
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada")
    
    # Obtener conceptos
    repo_concepto = RepositorioConceptoOrdenTrabajo(db)
    conceptos = repo_concepto.listar_por_orden(orden_id)
    
    # Obtener cliente
    from app.modulos.clientes.clientes_repositorio import RepositorioCliente
    repo_cliente = RepositorioCliente(db)
    cliente = repo_cliente.obtener(orden.cliente_id)
    
    # Obtener técnico si está asignado
    tecnico = None
    if orden.tecnico_asignado_id:
        from app.modulos.usuarios.usuarios_repositorio import RepositorioUsuario
        repo_usuario = RepositorioUsuario(db)
        tecnico = repo_usuario.obtener(orden.tecnico_asignado_id)
    
    return TEMPLATES.TemplateResponse(
        "ui/ordenes_trabajo/detalle.html",
        {
            "request": request,
            "usuario": usuario,
            "orden": orden,
            "conceptos": conceptos,
            "cliente": cliente,
            "tecnico": tecnico,
        }
    )


# Router principal que combina todos los sub-routers
router = APIRouter()
router.include_router(router_api)
router.include_router(router_ui)
router.include_router(router_extra_ui)
router.include_router(router_extra_api)
