"""Router y descriptor CRUD para cotizaciones usando factory pattern."""
from typing import Any
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Body, HTTPException, Response, Query
from sqlmodel import Session

from app.base.descriptor_crud import DescriptorCRUD
from app.base.factory_modulo import crear_modulo_crud
from app.nucleo.base_datos import obtener_sesion_bd, obtener_motor
from app.rutas.dependencias import dp_usuario_actual
from app.rutas.permisos import para_modulo
from app.modulos.cotizaciones.cotizaciones_esquemas import CotizacionRead, CotizacionCreate, CotizacionUpdate
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion, RepositorioConcepto
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.modulos.cotizaciones.pdf_generator import generar_pdf_cotizacion
from app.base.excepciones import RecursoNoEncontradoError, ReglaNegocioError

# Importar routers adicionales
from app.modulos.cotizaciones import conceptos_router, wizard_router



# ---------- Router Extras (Funcionalidad avanzada) ----------
router_extras = APIRouter(prefix="/api/cotizaciones", tags=["Cotizaciones - Extras"])

@router_extras.get("/{cotizacion_id}/completa")
def obtener_completa(
    cotizacion_id: int,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(dp_usuario_actual),
):
    """Obtiene una cotización con sus conceptos (para edición)."""
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    from app.modulos.cotizaciones.cotizaciones_esquemas import ConceptoRead
    
    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise RecursoNoEncontradoError("Cotización no encontrada")
    
    # Obtener conceptos usando repository existente
    repo = RepositorioCotizacion(db)
    conceptos = repo.obtener_conceptos(cotizacion_id)
    
    # Convertir a dict y agregar conceptos
    cotizacion_dict = cotizacion.model_dump()
    cotizacion_dict["conceptos"] = [
        ConceptoRead.model_validate(c) for c in conceptos
    ]
    
    return cotizacion_dict


@router_extras.get("/{cotizacion_id}/pdf")
def descargar_pdf(
    cotizacion_id: int,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(dp_usuario_actual),
):
    """Genera y descarga el PDF de una cotización."""
    try:
        pdf_bytes = generar_pdf_cotizacion(cotizacion_id, db)
        
        from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
        cotizacion = db.get(Cotizacion, cotizacion_id)
        filename = f"{cotizacion.numero if cotizacion else 'cotizacion'}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'}
        )
    except ValueError as e:
        raise RecursoNoEncontradoError(str(e))
    except Exception as e:
        raise ReglaNegocioError(f"Error generando PDF: {str(e)}")


@router_extras.patch("/{cotizacion_id}/notas-privadas")
def actualizar_notas_privadas(
    cotizacion_id: int,
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones")),
):
    """Actualiza únicamente las notas privadas de una cotización."""
    repo = RepositorioCotizacion(db)
    try:
        cotizacion = repo.actualizar_notas_privadas(
            cotizacion_id,
            data.get('notas_privadas'),
            usuario.usuario
        )
        return {"detail": "Notas privadas actualizadas", "notas_privadas": cotizacion.notas_privadas}
    except RecursoNoEncontradoError:
        raise


@router_extras.post("/completa")
def crear_cotizacion_completa(
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones")),
):
    """Crea una cotización completa con conceptos en una transacción."""
    from app.modulos.cotizaciones.cotizaciones_servicios import ServicioCreacionCotizacion
    
    # Delegar al servicio de dominio (mejora POO previa)
    servicio = ServicioCreacionCotizacion(db)
    cotizacion = servicio.crear_cotizacion_completa(data, usuario.usuario)
    
    return {
        "id": cotizacion.id, 
        "numero": cotizacion.numero, 
        "numero_version": cotizacion.numero_version
    }


@router_extras.patch("/{cotizacion_id}/actualizar-sin-version")
def actualizar_sin_versionar(
    cotizacion_id: int,
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones")),
):
    """Actualiza cotización SIN crear versión."""
    from app.modulos.cotizaciones.versionamiento import actualizar_sin_versionar as actualizar_fn
    return actualizar_fn(cotizacion_id, data, db, usuario)


@router_extras.post("/{cotizacion_id}/nueva-version")
def crear_version(
    cotizacion_id: int,
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones")),
):
    """Crea nueva VERSIÓN de cotización."""
    from app.modulos.cotizaciones.versionamiento import crear_nueva_version as crear_version_fn
    return crear_version_fn(cotizacion_id, data, db, usuario)


@router_extras.post("/{id}/cerrar")
def cerrar_cotizacion(
    id: int,
    data: dict = Body(...),
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones")),
):
    cot = db.get(Cotizacion, id)
    if not cot:
        raise RecursoNoEncontradoError("Cotización no encontrada")
    
    # Obtener el estado del body (finalizada o cancelada)
    estado = data.get('estado', 'finalizada')
    if estado not in ['finalizada', 'cancelada']:
        estado = 'finalizada'
    
    cot.estado = estado
    db.add(cot)
    db.commit()
    return {"mensaje": f"Cotización cerrada como {estado}"}


# ---------- Descriptor ----------
descriptor = DescriptorCRUD[RepositorioCotizacion, CotizacionCreate, CotizacionUpdate, CotizacionRead, UsuarioIdentity](
    label="Cotizaciones",
    base_url="/api/cotizaciones",
    repo_factory=RepositorioCotizacion,
    schema_read=CotizacionRead,
    schema_create=CotizacionCreate,
    schema_update=CotizacionUpdate,
    campos_editables={
        "cliente_id", "metodo_pago", "forma_pago", "notas",
        "atencion_a", "estado", "notas_privadas"
    },
    filtros_permitidos={"estado", "cliente_id"},
    campo_busqueda="numero",
    columnas_incluir=["numero", "cliente_id", "fecha_emision", "total", "estado"],
    columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
    boton_crear={"texto": "✨ Nueva Cotización", "url": "/ui/cotizaciones/wizard", "modal": False},
)


# ---------- Router Combinado usando Factory ----------
router = crear_modulo_crud(
    descriptor=descriptor,
    obtener_sesion=obtener_sesion_bd,
    actor_dependency=dp_usuario_actual,
    write_dependency=para_modulo("cotizaciones"),
    tpl_filas="ui/cotizaciones/_filas.html",
    tpl_form="ui/cotizaciones/_form.html",
    routers_adicionales=[
        conceptos_router.router_ui,
        conceptos_router.router_api,
        wizard_router.router,
        router_extras,
    ],
)
