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
        columnas_incluir=["folio", "origen", "fecha_salida", "total", "estado", "id"],
        boton_crear=None  # Deshabilitar creación directa independiente
    )
)

def obtener_contexto_viaticos(db: Session) -> dict[str, Any]:
    from app.modulos.clientes.clientes_modelo import Cliente
    from app.modulos.usuarios.usuarios_modelo import Usuario
    return {
        "clientes": db.exec(select(Cliente).order_by(Cliente.nombre)).all(),
        "usuarios": db.exec(select(Usuario).order_by(Usuario.nombres)).all(),
        "opciones_transporte": [{"id": e, "nombre": e} for e in ["Camión", "Avión", "Taxi", "Auto Rentado"]],
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
    db: Session = Depends(obtener_sesion_bd)
):
    repo = RepositorioViatico(db)
    viatico = repo.obtener_por_id(id)
    return TEMPLATES.TemplateResponse("ui/viaticos/detalle.html", {"request": request, "viatico": viatico})

@router_ui_extras.get("/cotizaciones-cliente-html")
def opciones_cotizaciones_por_cliente(
    cliente_id: int, 
    db: Session = Depends(obtener_sesion_bd)
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

@router_api_extras.post("/{id}/{accion}")
def cambiar_estado_viatico(
    id: int,
    accion: str,
    db: Session = Depends(obtener_sesion_bd)
):
    repo = RepositorioViatico(db)
    viatico = repo.obtener_por_id(id)
    from app.base.excepciones import ReglaNegocioError
    
    if accion == "solicitar" and viatico.estado == "borrador":
        viatico.estado = "solicitado"
    elif accion == "aprobar" and viatico.estado in ["borrador", "solicitado"]:
        viatico.estado = "aprobado"
    elif accion == "cancelar" and viatico.estado != "cancelado":
        viatico.estado = "cancelado"
    else:
        raise ReglaNegocioError(f"No se puede {accion} el viático en estado {viatico.estado}")
        
    repo.guardar(viatico)
    return viatico

@router_api_extras.get("/disponibles-para-cotizacion")
def obtener_viaticos_disponibles(request: Request, db: Session = Depends(obtener_sesion_bd)):
    """Obtiene viáticos útiles para ser importados a una cotización."""
    viaticos = db.exec(select(Viatico).where(Viatico.estado != "cancelado")).all()
    return [{"id": v.id, "folio": v.folio, "proyecto": v.proyecto or "Viaje Múltiple", "total": float(v.total or 0)} for v in viaticos]

router = crear_modulo_crud_estandar(
    descriptor=descriptor,
    nombre_modulo="viaticos",
    include_select_endpoint=True,
    extra_context_provider=obtener_contexto_viaticos,
    routers_adicionales=[router_api_extras, router_ui_extras]
)
