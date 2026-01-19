"""Router y descriptor CRUD para cotizaciones usando factory pattern."""
from typing import Any
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from app.base.descriptor_crud import DescriptorCRUD
from app.base.factory_modulo import crear_modulo_crud
from app.nucleo.base_datos import obtener_sesion_bd, obtener_motor
from app.rutas.dependencias import exigir_roles, dp_usuario_actual
from app.modulos.cotizaciones.cotizaciones_esquemas import CotizacionRead, CotizacionCreate, CotizacionUpdate
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion, RepositorioConcepto
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.modulos.cotizaciones.pdf_generator import generar_pdf_cotizacion

# Importar routers adicionales
from app.modulos.cotizaciones import conceptos_router, wizard_router


def _campos_creacion(payload: CotizacionCreate, actor: UsuarioIdentity) -> dict[str, Any]:
    """Genera campos adicionales al crear una cotización."""
    from app.base.descriptor_crud import _auditoria_creacion_default
    
    # Crear repo temporal para generar número y fecha de vigencia
    with Session(obtener_motor()) as db:
        repo_temp = RepositorioCotizacion(db)
        numero = repo_temp.generar_siguiente_numero()
        fecha_vigencia = repo_temp.calcular_fecha_vigencia(date.today())
    
    # Combinar auditoría automática con lógica de negocio
    extras = _auditoria_creacion_default(payload, actor)
    extras.update({
        "numero": numero,
        "fecha_emision": date.today(),
        "fecha_vigencia": fecha_vigencia,
    })
    return extras


def _campos_actualizacion(payload: CotizacionUpdate, actor: UsuarioIdentity) -> dict[str, Any]:
    """Solo actualiza el campo modificado_por."""
    from app.base.descriptor_crud import _auditoria_actualizacion_default
    return _auditoria_actualizacion_default(payload, actor)


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
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    
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
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


@router_extras.patch("/{cotizacion_id}/notas-privadas")
def actualizar_notas_privadas(
    cotizacion_id: int,
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
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
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router_extras.post("/crear-completa")
def crear_cotizacion_completa(
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """Crea una cotización completa con conceptos en una transacción."""
    repo = RepositorioCotizacion(db)
    
    # Delegar toda la lógica al repositorio
    cotizacion = repo.crear_completa(data, usuario.usuario)
    
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
    usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """Actualiza cotización SIN crear versión."""
    from app.modulos.cotizaciones.versionamiento import actualizar_sin_versionar as actualizar_fn
    return actualizar_fn(cotizacion_id, data, db, usuario)


@router_extras.post("/{cotizacion_id}/nueva-version")
def crear_version(
    cotizacion_id: int,
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """Crea nueva VERSIÓN de cotización."""
    from app.modulos.cotizaciones.versionamiento import crear_nueva_version as crear_version_fn
    return crear_version_fn(cotizacion_id, data, db, usuario)


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
    campos_creacion_extra=_campos_creacion,
    campos_actualizacion_extra=_campos_actualizacion,
    filtros_permitidos={"estado", "cliente_id"},
    campo_busqueda="numero",
    columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
)


# ---------- Router Combinado usando Factory ----------
router = crear_modulo_crud(
    descriptor=descriptor,
    obtener_sesion=obtener_sesion_bd,
    actor_dependency=dp_usuario_actual,
    write_dependency=exigir_roles("admin"),
    tpl_filas="ui/cotizaciones/_filas.html",
    tpl_form="ui/cotizaciones/_form.html",
    routers_adicionales=[
        conceptos_router.router_ui,
        conceptos_router.router_api,
        wizard_router.router,
        router_extras,
    ],
)
