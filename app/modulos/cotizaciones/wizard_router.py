"""Endpoints para wizard y vistas HTML de cotizaciones."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from typing import Any
from sqlmodel import Session

from app.web.jinja import get_templates

from app.base.excepciones import RecursoNoEncontradoError, ReglaNegocioError

from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import dp_usuario_actual
from app.rutas.permisos import para_modulo
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.base.catalogos import ESTADOS_MEXICO

router = APIRouter(prefix="/ui/cotizaciones", tags=["Cotizaciones - Wizard & Views"])
TEMPLATES = get_templates()


@router.get("/wizard")
def mostrar_wizard_cotizacion(
    request: Request,
    id: int | None = None,
    db: Session = Depends(obtener_sesion_bd),
    usuario: Any = Depends(dp_usuario_actual),
):
    """Wizard para crear/editar cotización completa."""
    # Validación manual de permisos por acción
    accion = "editar" if id else "crear"
    from app.modulos.usuarios.usuarios_modelo import Usuario
    from sqlmodel import select
    from app.base.excepciones import PermisoDenegadoError

    u_db = db.exec(select(Usuario).where(Usuario.usuario == usuario.usuario)).first()
    if not u_db:
        raise RecursoNoEncontradoError("Usuario no encontrado")
        
    permisos = getattr(u_db, f"permisos_{accion}", []) or []
    if "cotizaciones" not in permisos:
        raise PermisoDenegadoError(f"No tienes permiso de {accion} para cotizaciones")

    return TEMPLATES.TemplateResponse(
        "ui/cotizaciones/wizard.html",
        {"request": request, "usuario": u_db, "estados": ESTADOS_MEXICO}
    )


@router.get("/{cotizacion_id}/detalle")
def ver_detalle_cotizacion(
    cotizacion_id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    usuario = Depends(para_modulo("cotizaciones", "ver")),
):
    """Vista de detalle de una cotización con gestión de conceptos."""
    from sqlmodel import select
    from app.modulos.clientes.clientes_modelo import Cliente
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import ConceptoOrdenTrabajo, OrdenTrabajo

    repo = RepositorioCotizacion(db)
    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise RecursoNoEncontradoError("Cotizacion no encontrada")

    cliente = db.get(Cliente, cotizacion.cliente_id)
    if not cliente:
        raise RecursoNoEncontradoError("Cliente asociado a la cotización no encontrado")
    conceptos = repo.obtener_conceptos(cotizacion_id)

    # Estado de OT por concepto: {concepto_id: {"estado": "libre"|"en_ot"|"completado", "numero_ot": ...}}
    estado_conceptos = repo.obtener_estado_conceptos(cotizacion_id)

    # RBAC context for detail view actions
    per_edit = getattr(usuario, "permisos_editar", []) or []
    per_create = getattr(usuario, "permisos_crear", []) or []
    
    puede_editar = "cotizaciones" in per_edit
    puede_crear_ordenes = "ordenes_trabajo" in per_create
    es_admin = getattr(usuario, "rol", "") == "admin"

    return TEMPLATES.TemplateResponse(
        "ui/cotizaciones/detalle.html",
        {
            "request": request,
            "usuario": usuario,
            "cotizacion": cotizacion,
            "cliente": cliente,
            "conceptos": conceptos,
            "estado_conceptos": estado_conceptos,
            "puede_editar": puede_editar,
            "puede_crear_ordenes": puede_crear_ordenes,
            "es_admin": es_admin,
        }
    )


@router.get("/{cotizacion_id}/editar")
def editar_cotizacion(
    cotizacion_id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual),
):
    """Redirige al wizard en modo edición."""
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    
    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise RecursoNoEncontradoError("Cotización no encontrada")
    
    if cotizacion.estado in ["modificada", "cerrada"]:
        raise ReglaNegocioError(
            "No se puede editar una cotización modificada. Use la versión más reciente." 
            # (Nota: ReglaNegocioError mapea a 409, que es adecuado para conflicto)
        )
    
    return RedirectResponse(url=f"/ui/cotizaciones/wizard?id={cotizacion_id}", status_code=302)


@router.get("/{cotizacion_id}/notas-privadas-modal")
def cargar_modal_notas_privadas(
    cotizacion_id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    usuario = Depends(para_modulo("cotizaciones", "ver")),
):
    """Carga el modal de notas privadas."""
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    
    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise RecursoNoEncontradoError("Cotización no encontrada")
    
    return TEMPLATES.TemplateResponse(
        "ui/cotizaciones/_notas_privadas_modal.html",
        {"request": request, "cotizacion": cotizacion}
    )
