from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Any
from datetime import date
from decimal import Decimal
from sqlmodel import Session
from pydantic import BaseModel
from app.base.descriptor_crud import DescriptorCRUD
from app.base.factory_modulo import crear_modulo_crud
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import dp_usuario_actual
from app.rutas.permisos import para_modulo
from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo
from app.modulos.ordenes.ordenes_esquemas import (
    OrdenTrabajoRead, OrdenTrabajoCreate, OrdenTrabajoUpdate, ConceptoOTRead
)
from app.modulos.ordenes.ordenes_repositorio import (
    RepositorioOrden, EmpalmeError, ConceptoYaAsignadoError, ConceptoCompletadoError
)
from app.modulos.ordenes.dependencias import obtener_repo_ordenes
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.modulos.ordenes.pdf_generator import generar_pdf_orden
from app.base.excepciones import RecursoNoEncontradoError


# ---------- Router Extras (API) ----------
router_extras = APIRouter(prefix="/api/ordenes", tags=["Ordenes - Extras"])

@router_extras.get("/{id}/pdf")
def descargar_pdf_orden(
    id: int,
    db: Session = Depends(obtener_sesion_bd),
    repo: RepositorioOrden = Depends(obtener_repo_ordenes),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Genera y descarga el PDF de la Orden de Trabajo."""
    try:
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


# ---------- Router Técnicos (prioritario: debe ir ANTES de /{entidad_id}) ----------
# Si va después, FastAPI captura 'tecnicos' como entidad_id cuando intenta parsear como int.
router_tecnicos = APIRouter(prefix="/api/ordenes", tags=["Ordenes - Extras"])

@router_tecnicos.get("/tecnicos", response_model=list[dict])
def listar_tecnicos(
    repo: RepositorioOrden = Depends(obtener_repo_ordenes),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Lista usuarios con rol 'tecnico' para asignación en el modal de creación."""
    tecnicos = repo.listar_tecnicos()
    return [{"id": t.id, "nombres": t.nombres, "usuario": t.usuario} for t in tecnicos]


# ---------- Crear OT desde cotización ----------

class PayloadCrearOT(BaseModel):
    cotizacion_id: int
    fecha_programada: date
    hora_programada: str
    duracion: int = 1
    tecnico_id: int | None = None
    concepto_ids: list[int] = []

@router_extras.post("/crear-desde-cotizacion", response_model=OrdenTrabajoRead)
def crear_desde_cotizacion(
    payload: PayloadCrearOT,
    repo: RepositorioOrden = Depends(obtener_repo_ordenes),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Crea una OT a partir de una cotización con conceptos seleccionados y técnico opcional."""
    try:
        ot = repo.crear_desde_cotizacion(
            cotizacion_id=payload.cotizacion_id,
            fecha_programada=payload.fecha_programada,
            hora_programada=payload.hora_programada,
            duracion=payload.duracion,
            usuario=usuario.usuario,
            concepto_ids=payload.concepto_ids,
            tecnico_id=payload.tecnico_id,
        )
        return ot
    except (RecursoNoEncontradoError, EmpalmeError, ConceptoYaAsignadoError):
        # ReglaNegocioError y RecursoNoEncontradoError son capturadas por el app_factory
        # Se re-lanzan para que el handler global las convierta a 409/404 correctamente
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))



# ---------- Completar concepto (irreversible) ----------

@router_extras.post("/{orden_id}/conceptos/{concepto_id}/completar", response_model=ConceptoOTRead)
def completar_concepto(
    orden_id: int,
    concepto_id: int,
    repo: RepositorioOrden = Depends(obtener_repo_ordenes),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Marca un concepto de la OT como completado. Acción irreversible."""
    try:
        return repo.completar_concepto(orden_id, concepto_id, usuario.usuario)
    except RecursoNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConceptoCompletadoError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ---------- Finalizar y Cancelar OT manual ----------

@router_extras.post("/{orden_id}/finalizar", response_model=OrdenTrabajoRead)
def finalizar_orden(
    orden_id: int,
    repo: RepositorioOrden = Depends(obtener_repo_ordenes),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Finaliza manualmente una Orden de Trabajo (útil si no tiene conceptos o se fuerza el cierre)."""
    try:
        return repo.finalizar_orden(orden_id)
    except RecursoNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router_extras.post("/{orden_id}/cancelar", response_model=OrdenTrabajoRead)
def cancelar_orden(
    orden_id: int,
    repo: RepositorioOrden = Depends(obtener_repo_ordenes),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Cancela una Orden de Trabajo y emite evento para ajustar la Cotización asociada."""
    try:
        return repo.cancelar_orden(orden_id)
    except RecursoNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

# ---------- Reasignar técnico ----------

class PayloadReasignarTecnico(BaseModel):
    tecnico_id: int | None = None

@router_extras.patch("/{orden_id}/tecnico", response_model=OrdenTrabajoRead)
def reasignar_tecnico(
    orden_id: int,
    payload: PayloadReasignarTecnico,
    repo: RepositorioOrden = Depends(obtener_repo_ordenes),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Reasigna o quita el técnico de una OT. Valida que no haya empalme de horario."""
    try:
        return repo.reasignar_tecnico(orden_id, payload.tecnico_id, usuario.usuario)
    except RecursoNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EmpalmeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


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


# ---------- Descriptor ----------
descriptor = DescriptorCRUD[OrdenTrabajo, OrdenTrabajoCreate, OrdenTrabajoUpdate, OrdenTrabajoRead, UsuarioIdentity](
    label="Ordenes de Trabajo",
    base_url="/api/ordenes",
    repo_factory=RepositorioOrden,
    schema_read=OrdenTrabajoRead,
    schema_create=OrdenTrabajoCreate,
    schema_update=OrdenTrabajoUpdate,
    campos_editables={"fecha_programada", "hora_programada", "domicilio", "contacto", "estado", "notas_publicas", "notas_privadas"},
    filtros_permitidos={"estado", "cliente_nombre"},
    campo_busqueda="numero_ot",
    columnas_incluir=["numero_ot", "fecha_programada", "cliente_nombre", "estado", "tecnico_nombre"],
    columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
    boton_crear={"texto": "📋 Ir a Cotizaciones", "url": "/cotizaciones", "modal": False},
)

# ---------- Router Factory ----------
router = crear_modulo_crud(
    descriptor=descriptor,
    obtener_sesion=obtener_sesion_bd,
    actor_dependency=dp_usuario_actual,
    write_dependency=para_modulo("ordenes"),
    tpl_filas="ui/ordenes/_filas.html",
    tpl_form="ui/ordenes/_form.html",
    routers_prioritarios=[router_tecnicos],          # /tecnicos ANTES de /{entidad_id}
    routers_adicionales=[router_extras, router_ui_extras]
)

