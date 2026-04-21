"""Router de Viáticos."""
from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select
from typing import Any

from app.base.descriptor_crud import DescriptorCRUD, ConfiguracionUI
from app.base.factory_modulo import crear_modulo_crud_estandar
from app.nucleo.base_datos import obtener_sesion_bd
from app.modulos.viaticos.viaticos_modelo import Viatico
from app.modulos.viaticos.viaticos_esquemas import ViaticoCreate, ViaticoUpdate, ViaticoRead
from app.modulos.viaticos.viaticos_repositorio import RepositorioViatico
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.rutas.permisos import para_modulo

descriptor = DescriptorCRUD[Viatico, ViaticoCreate, ViaticoUpdate, ViaticoRead, UsuarioIdentity](
    label="Viáticos",
    base_url="/api/viaticos",
    repo_factory=RepositorioViatico,
    schema_read=ViaticoRead,
    schema_create=ViaticoCreate,
    schema_update=ViaticoUpdate,
    campos_editables={
        "cliente_id", "responsable_id", "proyecto", "ot_ids", 
        "personas", "tipo_transporte", "cotizacion_id", "origen", "destino", "fecha_salida", "fecha_regreso",
        "costo_transporte", "costo_alojamiento", "costo_alimentos", "costo_otros",
        "notas_desglose", "estado"
    },
    campo_busqueda="folio",
    config_ui=ConfiguracionUI(
        topic="viaticos",
        columnas_incluir=["folio", "origen", "fecha_salida", "fecha_regreso", "total", "estado"],
        boton_crear={"texto": "📋 Crear desde Cotización", "url": "/ui/cotizaciones", "modal": False},
    )
)

def obtener_contexto_viaticos(db: Session) -> dict[str, Any]:
    from app.modulos.clientes.clientes_modelo import Cliente
    from app.modulos.usuarios.usuarios_modelo import Usuario
    from app.base.catalogos import ESTADOS_MEXICO
    return {
        "clientes": db.exec(select(Cliente).order_by(Cliente.nombre)).all(),
        "usuarios": db.exec(select(Usuario).order_by(Usuario.nombres)).all(),
        "estados": [{"id": e, "nombre": e} for e in ESTADOS_MEXICO],
        "opciones_transporte": [{"id": e, "nombre": e} for e in [
            "Vehículo Empresa", 
            "Vehículo Personal", 
            "Avión", 
            "Autobús", 
            "Taxi / Uber", 
            "Auto Rentado", 
            "Otro"
        ]],
        "cotizaciones": [] # Se llena dinámicamente vía HTMX, o en Update se podría cargar una por defecto
    }

router_ui_extras = APIRouter(prefix="/ui/viaticos", tags=["Viáticos - UI Extras"])
router_api_extras = APIRouter(prefix="/api/viaticos", tags=["Viáticos - Acciones"])

from app.web.jinja import get_templates
TEMPLATES = get_templates()

@router_ui_extras.get("/{id}/detalle")
def ver_detalle_viatico(
    id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    usuario = Depends(para_modulo("viaticos", "ver"))
):
    repo = RepositorioViatico(db)
    viatico = repo.obtener_por_id(id)
    if not viatico:
        from app.base.excepciones import RecursoNoEncontradoError
        raise RecursoNoEncontradoError(f"Viático con ID {id} no encontrado")
    
    # Contexto RBAC
    perms_edit = getattr(usuario, "permisos_editar", []) or []
    perms_delete = getattr(usuario, "permisos_eliminar", []) or []
    
    puede_editar = "viaticos" in perms_edit
    puede_eliminar = "viaticos" in perms_delete
    es_admin = getattr(usuario, "rol", "") == "admin"

    return TEMPLATES.TemplateResponse(
        "ui/viaticos/detalle.html", 
        {
            "request": request, 
            "viatico": viatico, 
            "usuario": usuario,
            "puede_editar": puede_editar,
            "puede_eliminar": puede_eliminar,
            "es_admin": es_admin
        }
    )

@router_ui_extras.get("/cotizaciones-cliente-html")
def opciones_cotizaciones_por_cliente(
    cliente_id: int, 
    db: Session = Depends(obtener_sesion_bd),
    _usuario = Depends(para_modulo("viaticos", "ver"))
):
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    from fastapi.responses import HTMLResponse
    cotizaciones = db.exec(
        select(Cotizacion)
        .where(Cotizacion.cliente_id == cliente_id)
        .where(Cotizacion.estado.notin_(["cancelada", "finalizada", "cerrada", "modificada", "rechazada"]))
        .order_by(Cotizacion.id.desc())
    ).all()
    
    html = '<option value="">-- Seleccionar --</option>'
    for c in cotizaciones:
        html += f'<option value="{c.id}">{c.numero}</option>'
    return HTMLResponse(content=html)

@router_ui_extras.get("/ot-disponibles-html")
def ot_disponibles_por_cotizacion(
    cotizacion_id: int,
    viatico_id: int | None = None,
    db: Session = Depends(obtener_sesion_bd),
    _usuario = Depends(para_modulo("viaticos", "ver"))
):
    from app.modulos.ordenes_trabajo.ordenes_trabajo_repositorio import RepositorioOrden
    from fastapi.responses import HTMLResponse
    repo_ot = RepositorioOrden(db)
    ots = repo_ot.obtener_por_cotizacion(cotizacion_id)
    
    seleccionados = set()
    if viatico_id:
        from app.modulos.viaticos.viaticos_repositorio import RepositorioViatico
        repo_v = RepositorioViatico(db)
        v = repo_v.obtener_por_id(viatico_id)
        if v:
            seleccionados = {ot.id for ot in v.rutas_ot}

    if not ots:
        return HTMLResponse(content='<p class="text-muted small italic p-2 border rounded bg-light">No hay órdenes de trabajo generadas para esta cotización.</p>')
    
    html = '<div class="row g-2">'
    for ot in ots:
        fecha_str = ot.fecha_programada.isoformat() if ot.fecha_programada else ""
        checked = "checked" if ot.id in seleccionados else ""
        html += f'''
        <div class="col-12 mb-2">
            <div class="form-check p-3 border rounded shadow-sm bg-white ot-card-link" data-fecha="{fecha_str}" style="cursor: pointer; transition: all 0.2s; border-left: 4px solid #7ed6df !important;">
                <input class="form-check-input ms-0 me-3" type="checkbox" name="ot_ids" value="{ot.id}" id="ot_{ot.id}" {checked} style="transform: scale(1.3); cursor: pointer;">
                <label class="form-check-label small w-100" for="ot_{ot.id}" style="cursor: pointer;">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="fw-bold text-primary" style="font-size: 0.95rem;">{ot.numero_ot}</span>
                        <span class="badge {'bg-success text-white' if ot.estado == 'finalizada' else 'bg-warning text-dark'} px-2 py-1" style="font-size: 0.75rem;">{ot.estado.upper()}</span>
                    </div>
                    <div class="text-muted mt-2 d-flex align-items-center">
                        <i class="far fa-calendar-alt me-2 text-info"></i> 
                        <span class="fw-medium">{ot.fecha_programada.strftime('%d/%m/%Y') if ot.fecha_programada else 'S/F'}</span>
                        <span class="ms-auto text-muted small"><i class="fas fa-chevron-right opacity-50"></i></span>
                    </div>
                </label>
            </div>
        </div>
'''
    html += '</div>'
    return HTMLResponse(content=html)

@router_api_extras.post("/{id}/{accion}")
def cambiar_estado_viatico(
    id: int,
    accion: str,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("viaticos", "editar"))
):
    from app.modulos.viaticos.viaticos_servicios import ServicioViaticos
    srv = ServicioViaticos(db)
    return srv.cambiar_estado(id, accion, usuario.nombre)

@router_api_extras.get("/disponibles-para-cotizacion")
def obtener_viaticos_disponibles(
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(para_modulo("viaticos", "ver"))
):
    viaticos = db.exec(select(Viatico).where(Viatico.estado != "cancelado")).all()
    return [{"id": v.id, "folio": v.folio, "proyecto": v.proyecto or "Viaje Múltiple", "total": float(v.total or 0)} for v in viaticos]

router = crear_modulo_crud_estandar(
    descriptor=descriptor,
    nombre_modulo="viaticos",
    include_select_endpoint=True,
    extra_context_provider=obtener_contexto_viaticos,
    routers_prioritarios=[router_api_extras, router_ui_extras]
)
