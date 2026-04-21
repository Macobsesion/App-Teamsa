"""Endpoints para gestión de conceptos en cotizaciones (UI y API)."""
from decimal import Decimal
from fastapi import APIRouter, Depends, Body, Request
from sqlmodel import Session

from app.web.jinja import get_templates
TEMPLATES = get_templates()

from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import dp_usuario_actual
from app.rutas.permisos import para_modulo
from app.modulos.cotizaciones.cotizaciones_esquemas import ConceptoCreate, ConceptoRead
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion, RepositorioConcepto
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity

router_ui = APIRouter(prefix="/ui/cotizaciones", tags=["Cotizaciones - Conceptos UI"])
router_api = APIRouter(prefix="/api/cotizaciones", tags=["Cotizaciones - Conceptos API"])

TEMPLATES = get_templates()


# ========== UI/HTMX Endpoints ==========

@router_ui.get("/{cotizacion_id}/concepto-form")
def mostrar_formulario_concepto(
    cotizacion_id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(dp_usuario_actual),
):
    """Formulario para agregar concepto (modal HTMX)."""
    return TEMPLATES.TemplateResponse(
        "ui/cotizaciones/_concepto_form.html",
        {"request": request, "cotizacion_id": cotizacion_id}
    )


@router_ui.post("/{cotizacion_id}/conceptos")
def agregar_concepto_htmx(
    cotizacion_id: int,
    servicio_id: int,
    codigo_sat: str,
    descripcion: str,
    unidad: str,
    cantidad: float,
    precio_unitario: float,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones")),
    descuento_porcentaje: float = 0.0,
):
    """Agrega concepto y devuelve lista actualizada (HTMX)."""
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    
    # Agregar concepto
    repo_concepto = RepositorioConcepto(db)
    repo_concepto.crear_concepto(
        cotizacion_id=cotizacion_id,
        servicio_id=servicio_id,
        codigo_sat=codigo_sat,
        descripcion=descripcion,
        unidad=unidad,
        cantidad=Decimal(str(cantidad)),
        precio_unitario=Decimal(str(precio_unitario)),
        descuento_porcentaje=Decimal(str(descuento_porcentaje))
    )
    
    # Devolver lista actualizada
    repo = RepositorioCotizacion(db)
    cotizacion = db.get(Cotizacion, cotizacion_id)
    conceptos = repo.obtener_conceptos(cotizacion_id)
    
    return TEMPLATES.TemplateResponse(
        "ui/cotizaciones/_conceptos_list.html",
        {"request": request, "cotizacion": cotizacion, "conceptos": conceptos}
    )


@router_ui.delete("/{cotizacion_id}/conceptos/{concepto_id}")
def eliminar_concepto_htmx(
    cotizacion_id: int,
    concepto_id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones")),
):
    """Elimina concepto y devuelve lista actualizada (HTMX)."""
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    
    repo_concepto = RepositorioConcepto(db)
    repo_concepto.eliminar_concepto(concepto_id, cotizacion_id)
    
    repo = RepositorioCotizacion(db)
    cotizacion = db.get(Cotizacion, cotizacion_id)
    conceptos = repo.obtener_conceptos(cotizacion_id)
    
    return TEMPLATES.TemplateResponse(
        "ui/cotizaciones/_conceptos_list.html",
        {"request": request, "cotizacion": cotizacion, "conceptos": conceptos}
    )


# ========== JSON API Endpoints ==========

@router_api.post("/{cotizacion_id}/conceptos", response_model=ConceptoRead)
def agregar_concepto_api(
    cotizacion_id: int,
    concepto: ConceptoCreate,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones")),
):
    """Agrega un concepto a una cotización (API JSON)."""
    repo = RepositorioConcepto(db)
    return repo.crear_concepto(
        cotizacion_id=cotizacion_id,
        servicio_id=concepto.servicio_id,
        codigo_sat=concepto.codigo_sat,
        descripcion=concepto.descripcion,
        unidad=concepto.unidad,
        cantidad=concepto.cantidad,
        precio_unitario=concepto.precio_unitario
    )


@router_api.delete("/{cotizacion_id}/conceptos/{concepto_id}")
def eliminar_concepto_api(
    cotizacion_id: int,
    concepto_id: int,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones")),
):
    """Elimina un concepto (API JSON)."""
    repo = RepositorioConcepto(db)
    repo.eliminar_concepto(concepto_id, cotizacion_id)
    return {"detail": "Concepto eliminado"}
