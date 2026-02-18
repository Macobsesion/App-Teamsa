from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Any
from datetime import date
from decimal import Decimal
from sqlmodel import Session
from pydantic import BaseModel
from app.base.descriptor_crud import DescriptorCRUD
from app.base.factory_modulo import crear_modulo_crud
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import dp_usuario_actual, exigir_roles
from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo
from app.modulos.ordenes.ordenes_esquemas import OrdenTrabajoRead, OrdenTrabajoCreate, OrdenTrabajoUpdate
from app.modulos.ordenes.ordenes_repositorio import RepositorioOrden
from app.modulos.ordenes.dependencias import obtener_repo_ordenes
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.modulos.ordenes.pdf_generator import generar_pdf_orden


# ---------- Router Extras (API) ----------
router_extras = APIRouter(prefix="/api/ordenes", tags=["Ordenes - Extras"])

@router_extras.get("/{id}/pdf")
def descargar_pdf_orden(
    id: int,
    db: Session = Depends(obtener_sesion_bd),
    # Nota: Para PDF aún necesitamos DB session directa para pdf_generator, 
    # pero podríamos mover esa lógica al repo eventualmente.
    # Por ahora usamos el repo inyectado para buscar la OT.
    repo: RepositorioOrden = Depends(obtener_repo_ordenes),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Genera y descarga el PDF de la Orden de Trabajo."""
    try:
        # Generar PDF bytes (Lógica legacy que pide session directa)
        pdf_bytes = generar_pdf_orden(id, db)
        
        ot = repo.obtener_por_id(id)
        if not ot:
             raise HTTPException(status_code=404, detail="Orden no encontrada")
             
        filename = f"Orden_{ot.numero_ot}.pdf"
        
        from fastapi.responses import Response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


# ---------- Router UI Extras ----------
from fastapi.templating import Jinja2Templates
from fastapi import Request
TEMPLATES = Jinja2Templates(directory="web/templates")
router_ui_extras = APIRouter(prefix="/ui/ordenes", tags=["Ordenes - UI"])

@router_ui_extras.get("/{id}/detalle")
def ver_detalle_orden(
    id: int,
    request: Request,
    repo: RepositorioOrden = Depends(obtener_repo_ordenes),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Vista de detalle de una Orden de Trabajo."""
    ot = repo.obtener_por_id(id)
    if not ot:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    return TEMPLATES.TemplateResponse(
        "ui/ordenes/detalle.html",
        {
            "request": request,
            "usuario": usuario,
            "ot": ot,
        }
    )

class PayloadCrearOT(BaseModel):
    cotizacion_id: int
    fecha_programada: date
    hora_programada: str
    duracion: int = 1

@router_extras.post("/crear-desde-cotizacion", response_model=OrdenTrabajoRead)

def crear_desde_cotizacion(
    payload: PayloadCrearOT,
    repo: RepositorioOrden = Depends(obtener_repo_ordenes),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    ot = repo.crear_desde_cotizacion(
        cotizacion_id=payload.cotizacion_id,
        fecha_programada=payload.fecha_programada,
        hora_programada=payload.hora_programada,
        duracion=payload.duracion,
        usuario=usuario.usuario
    )
    return ot

# ---------- Descriptor ----------
descriptor = DescriptorCRUD[OrdenTrabajo, OrdenTrabajoCreate, OrdenTrabajoUpdate, OrdenTrabajoRead, UsuarioIdentity](
    label="Ordenes de Trabajo",
    base_url="/api/ordenes",
    repo_factory=RepositorioOrden,
    schema_read=OrdenTrabajoRead,
    schema_create=OrdenTrabajoCreate,  # No se usa directamente en UI, pero requerido por tipos
    schema_update=OrdenTrabajoUpdate,
    campos_editables={"fecha_programada", "hora_programada", "domicilio", "contacto", "estado", "notas_publicas", "notas_privadas"},
    filtros_permitidos={"estado", "cliente_nombre"},
    campo_busqueda="numero_ot",
    columnas_incluir=["numero_ot", "fecha_programada", "cliente_nombre", "estado"],
    columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
    boton_crear={"texto": "📋 Ir a Cotizaciones", "url": "/cotizaciones", "modal": False},
)

# ---------- Router Factory ----------
router = crear_modulo_crud(
    descriptor=descriptor,
    obtener_sesion=obtener_sesion_bd,
    actor_dependency=dp_usuario_actual,
    write_dependency=exigir_roles("admin"),
    tpl_filas="ui/ordenes/_filas.html",
    tpl_form="ui/ordenes/_form.html",
    routers_adicionales=[router_extras, router_ui_extras]
)
