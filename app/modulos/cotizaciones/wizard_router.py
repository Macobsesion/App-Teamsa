"""Endpoints para wizard y vistas HTML de cotizaciones."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app.base.excepciones import RecursoNoEncontradoError, ReglaNegocioError

from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import exigir_roles, dp_usuario_actual
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity

router = APIRouter(prefix="/ui/cotizaciones", tags=["Cotizaciones - Wizard & Views"])
TEMPLATES = Jinja2Templates(directory="web/templates")


@router.get("/wizard")
def mostrar_wizard_cotizacion(
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """Wizard para crear/editar cotización completa."""
    return TEMPLATES.TemplateResponse(
        "ui/cotizaciones/wizard.html",
        {"request": request, "usuario": usuario}
    )


@router.get("/{cotizacion_id}/detalle")
def ver_detalle_cotizacion(
    cotizacion_id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual),
):
    """Vista de detalle de una cotización con gestión de conceptos."""
    from sqlmodel import select
    from app.modulos.clientes.clientes_modelo import Cliente
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    from app.modulos.ordenes.ordenes_modelo import ConceptoOrdenTrabajo, OrdenTrabajo

    repo = RepositorioCotizacion(db)
    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise RecursoNoEncontradoError("Cotizacion no encontrada")

    cliente = db.get(Cliente, cotizacion.cliente_id)
    conceptos = repo.obtener_conceptos(cotizacion_id)

    # Estado de OT por concepto: {concepto_id: {"estado": "libre"|"en_ot"|"completado", "numero_ot": ...}}
    concepto_ids = [c.id for c in conceptos]
    estado_conceptos: dict[int, dict] = {}

    if concepto_ids:
        filas = db.exec(
            select(ConceptoOrdenTrabajo, OrdenTrabajo)
            .join(OrdenTrabajo, ConceptoOrdenTrabajo.orden_id == OrdenTrabajo.id)
            .where(ConceptoOrdenTrabajo.concepto_cotizacion_id.in_(concepto_ids))
        ).all()

        for c_ot, ot in filas:
            estado_conceptos[c_ot.concepto_cotizacion_id] = {
                "estado": c_ot.estado,        # "pendiente" o "completado"
                "numero_ot": ot.numero_ot,
                "orden_id": ot.id,
            }

    return TEMPLATES.TemplateResponse(
        "ui/cotizaciones/detalle.html",
        {
            "request": request,
            "usuario": usuario,
            "cotizacion": cotizacion,
            "cliente": cliente,
            "conceptos": conceptos,
            "estado_conceptos": estado_conceptos,   # nuevo
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
    _usuario: UsuarioIdentity = Depends(dp_usuario_actual),
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
