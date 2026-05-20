from typing import Any
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Body, Response, Query
from sqlmodel import Session

from app.base.descriptor_crud import DescriptorCRUD, ConfiguracionUI
from app.base.factory_modulo import crear_modulo_crud_estandar
from app.nucleo.base_datos import obtener_sesion_bd, obtener_motor
from app.rutas.dependencias import dp_usuario_actual
from app.rutas.permisos import para_modulo
from app.modulos.cotizaciones.cotizaciones_esquemas import (
    CotizacionRead, CotizacionCreate, CotizacionUpdate, ConceptoRead, CotizacionWizardRead
)
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion, RepositorioConcepto
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.modulos.cotizaciones.pdf_generator import generar_pdf_cotizacion
from app.base.excepciones import RecursoNoEncontradoError, ReglaNegocioError

# Importar routers adicionales
from app.modulos.cotizaciones import conceptos_router, wizard_router, viaticos_wizard_router



# ---------- Router Extras (Funcionalidad avanzada) ----------
router_extras = APIRouter(prefix="/api/cotizaciones", tags=["Cotizaciones - Extras"])

# ---------- Router Wizard API (Específico para la lógica del Wizard) ----------
router_wizard_api = APIRouter(prefix="/api/wizard/cotizaciones", tags=["Cotizaciones - Wizard API"])

@router_wizard_api.get("/{cotizacion_id}/completa", response_model=CotizacionWizardRead)
@router_wizard_api.get("/{cotizacion_id}/completa/", response_model=CotizacionWizardRead)
def obtener_completa(
    cotizacion_id: int,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(dp_usuario_actual),
):
    """Obtiene una cotización con sus conceptos (para edición)."""
    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise RecursoNoEncontradoError("Cotización no encontrada")

    repo = RepositorioCotizacion(db)
    cotizacion.conceptos = repo.obtener_conceptos(cotizacion_id)

    return cotizacion


@router_extras.get("/{cotizacion_id}/pdf")
@router_extras.get("/{cotizacion_id}/pdf/")
def descargar_pdf(
    cotizacion_id: int,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(dp_usuario_actual),
):
    """Genera y descarga el PDF de una cotización."""
    pdf_bytes = generar_pdf_cotizacion(cotizacion_id, db)
    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise RecursoNoEncontradoError("Cotización no encontrada")
    filename = f"{cotizacion.numero}.pdf"
    
    # Auditoría: Descarga de documento
    from app.base.logs_servicio import ServicioLogs
    ServicioLogs.registrar(usuario=_usuario.usuario, accion="DESCARGAR", modulo="cotizaciones", detalles=f"PDF {filename}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router_extras.patch("/{cotizacion_id}/notas-privadas")
@router_extras.patch("/{cotizacion_id}/notas-privadas/")
def actualizar_notas_privadas(
    cotizacion_id: int,
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones")),
):
    """Actualiza únicamente las notas privadas de una cotización."""
    repo = RepositorioCotizacion(db)
    cotizacion = repo.actualizar_notas_privadas(
        cotizacion_id,
        data.get('notas_privadas'),
        usuario.usuario
    )
    
    # Auditoría: Notas privadas
    from app.base.logs_servicio import ServicioLogs
    ServicioLogs.registrar(usuario=usuario.usuario, accion="EDITAR", modulo="cotizaciones", detalles=f"Notas privadas de {cotizacion.numero}")

    return {"detail": "Notas privadas actualizadas", "notas_privadas": cotizacion.notas_privadas}


@router_wizard_api.post("/completa")
@router_wizard_api.post("/completa/")
def crear_cotizacion_completa(
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones", "crear")),
):
    """Crea una cotización completa con conceptos en una transacción."""
    from app.modulos.cotizaciones.cotizaciones_servicios import ServicioCotizaciones
    
    servicio = ServicioCotizaciones(db)
    cotizacion = servicio.crear_cotizacion_completa(data, usuario.usuario)
    
    # Auditoría: Creación desde Wizard
    from app.base.logs_servicio import ServicioLogs
    ServicioLogs.registrar(usuario=usuario.usuario, accion="CREAR", modulo="cotizaciones", detalles=f"Cotización {cotizacion.numero} (Wizard)")

    return {
        "id": cotizacion.id, 
        "numero": cotizacion.numero, 
        "numero_version": cotizacion.numero_version
    }


@router_wizard_api.patch("/{cotizacion_id}/actualizar-sin-version")
@router_wizard_api.patch("/{cotizacion_id}/actualizar-sin-version/")
def actualizar_sin_versionar(
    cotizacion_id: int,
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones")),
):
    """Actualiza cotización SIN crear versión."""
    from app.modulos.cotizaciones.cotizaciones_servicios import ServicioCotizaciones
    servicio = ServicioCotizaciones(db)
    return servicio.actualizar_sin_versionar(cotizacion_id, data, usuario.usuario)


@router_wizard_api.post("/{cotizacion_id}/nueva-version")
@router_wizard_api.post("/{cotizacion_id}/nueva-version/")
def crear_version(
    cotizacion_id: int,
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones")),
):
    """Crea nueva VERSIÓN de cotización."""
    from app.modulos.cotizaciones.cotizaciones_servicios import ServicioCotizaciones
    servicio = ServicioCotizaciones(db)
    res = servicio.crear_nueva_version(cotizacion_id, data, usuario.usuario)
    
    # Auditoría: Nueva versión
    from app.base.logs_servicio import ServicioLogs
    ServicioLogs.registrar(usuario=usuario.usuario, accion="VERSIONAR", modulo="cotizaciones", detalles=f"Nueva versión de ID {cotizacion_id}")

    return res


@router_extras.post("/{id}/cerrar")
@router_extras.post("/{id}/cerrar/")
def cerrar_cotizacion(
    id: int,
    data: dict = Body(...),
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("cotizaciones")),
):
    from app.modulos.cotizaciones.cotizaciones_servicios import ServicioCotizaciones
    
    servicio = ServicioCotizaciones(db)
    motivo = data.get('motivo', 'Cerrada por usuario')
    forzar = data.get('forzar', False)
    estado_final = data.get('estado', 'cancelada')
    
    servicio.cerrar_cotizacion(id, motivo, forzar=forzar, estado_final=estado_final)
    return {"mensaje": f"Cotización cerrada correctamente"}


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
    config_ui=ConfiguracionUI(
        topic="cotizaciones",
        columnas_incluir=["numero", "cliente_id", "ejecucion_ot", "fecha_emision", "total", "estado"],
        columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
        boton_crear={"texto": "✨ Nueva Cotización", "url": "/ui/cotizaciones/wizard", "modal": False},
    )
)


# ---------- Router Combinado usando Factory ----------
router = crear_modulo_crud_estandar(
    descriptor=descriptor,
    nombre_modulo="cotizaciones",
    routers_prioritarios=[
        router_extras,
        router_wizard_api,
        conceptos_router.router_ui,
        conceptos_router.router_api,
        wizard_router.router,
        viaticos_wizard_router.router_ui,
    ],
)
