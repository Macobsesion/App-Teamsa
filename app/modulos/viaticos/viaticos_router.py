"""Router y descriptor CRUD para viáticos con endpoint de PDF."""
from typing import Any
from datetime import date

from fastapi import APIRouter, Depends, HTTPException  # type: ignore
from fastapi.responses import Response  # type: ignore
from sqlmodel import Session  # type: ignore

from app.base.descriptor_crud import DescriptorCRUD
from app.base.ui_crud import DescriptorUI, construir_enrutador_ui
from app.nucleo.base_datos import obtener_sesion_bd, obtener_motor
from app.rutas.dependencias import exigir_roles, dp_usuario_actual
from app.modulos.viaticos.viaticos_esquemas import (
    ViaticoRead,
    ViaticoCreate,
    ViaticoUpdate,
    GastoCreate,
    GastoRead,
)
from app.modulos.viaticos.viaticos_repositorio import (
    RepositorioViatico,
    RepositorioGasto,
)
from app.modulos.viaticos.pdf_generator import generar_pdf_viatico
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity


def _campos_creacion(payload: ViaticoCreate, actor: UsuarioIdentity) -> dict[str, Any]:
    """Genera campos adicionales al crear un viático."""
    from app.base.descriptor_crud import _auditoria_creacion_default
    
    # Crear repo temporal para generar número y calcular días
    with Session(obtener_motor()) as db:
        repo_temp = RepositorioViatico(db)
        numero = repo_temp.generar_siguiente_numero()
        dias = repo_temp.calcular_dias(payload.fecha_inicio, payload.fecha_fin)
    
    # Combinar auditoría automática con lógica de negocio
    extras = _auditoria_creacion_default(payload, actor)
    extras.update({
        "numero": numero,
        "dias": dias,
    })
    return extras


def _campos_actualizacion(payload: ViaticoUpdate, actor: UsuarioIdentity) -> dict[str, Any]:
    """Recalcula días si cambian las fechas."""
    from app.base.descriptor_crud import _auditoria_actualizacion_default
    
    extras = _auditoria_actualizacion_default(payload, actor)
    
    # Si cambian fechas, recalcular días
    if payload.fecha_inicio and payload.fecha_fin:
        with Session(obtener_motor()) as db:
            repo_temp = RepositorioViatico(db)
            dias = repo_temp.calcular_dias(payload.fecha_inicio, payload.fecha_fin)
            extras["dias"] = dias
    
    return extras


# Descriptor declarativo del módulo
descriptor = DescriptorCRUD[RepositorioViatico, ViaticoCreate, ViaticoUpdate, ViaticoRead, UsuarioIdentity](
    label="Viáticos",
    base_url="/api/viaticos",
    repo_factory=RepositorioViatico,  # Clase directa
    schema_read=ViaticoRead,
    schema_create=ViaticoCreate,
    schema_update=ViaticoUpdate,
    campos_editables={
        "responsable_id", "proyecto", "cliente", "destino",
        "fecha_inicio", "fecha_fin", "estado", "notas", "observaciones"
    },
    campos_creacion_extra=_campos_creacion,
    campos_actualizacion_extra=_campos_actualizacion,
    filtros_permitidos={"estado", "responsable_id"},
    campo_busqueda="numero",
    columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
)

# Router API JSON
router_api = descriptor.to_api_router(
    obtener_sesion=obtener_sesion_bd,
    write_dependency=exigir_roles("admin"),
)

# Router UI HTML/HTMX
router_ui = construir_enrutador_ui(
    prefix="/ui/viaticos",
    repo_factory=RepositorioViatico,
    schema_create=ViaticoCreate,
    schema_update=ViaticoUpdate,
    hooks=descriptor.build_hooks(),
    obtener_sesion=obtener_sesion_bd,
    list_dependencies=[Depends(dp_usuario_actual)],
    write_dependency=exigir_roles("admin"),
    ui=DescriptorUI(
        tpl_filas="ui/viaticos/_filas.html",
        tpl_form="ui/viaticos/_form.html",
    ),
    label=descriptor.label,
    actor_dependency=dp_usuario_actual,
    columnas=descriptor.frontend_config().get("columnas"),
    campo_busqueda=descriptor.campo_busqueda,
)

# Router adicional para gastos y PDF
router_extra = APIRouter(prefix="/api/viaticos", tags=["Viáticos"])


@router_extra.post("/{viatico_id}/gastos", response_model=GastoRead)
def agregar_gasto(
    viatico_id: int,
    gasto: GastoCreate,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """Agrega un gasto a un viático y recalcula totales."""
    repo = RepositorioGasto(db)
    return repo.crear(
        viatico_id=viatico_id,
        categoria=gasto.categoria,
        concepto=gasto.concepto,
        cantidad=gasto.cantidad,
        precio_unitario=gasto.precio_unitario,
        fecha_gasto=gasto.fecha_gasto,
        tiene_factura=gasto.tiene_factura,
        numero_factura=gasto.numero_factura,
    )


@router_extra.delete("/{viatico_id}/gastos/{gasto_id}")
def eliminar_gasto(
    viatico_id: int,
    gasto_id: int,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """Elimina un gasto de un viático y recalcula totales."""
    repo = RepositorioGasto(db)
    repo.eliminar(gasto_id, viatico_id)
    return {"detail": "Gasto eliminado"}


@router_extra.get("/{viatico_id}/pdf")
def descargar_pdf(
    viatico_id: int,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """Genera y descarga el PDF de un viático."""
    try:
        pdf_bytes = generar_pdf_viatico(viatico_id, db)
        
        # Obtener número de viático para el filename
        from app.modulos.viaticos.viaticos_modelo import Viatico
        viatico = db.get(Viatico, viatico_id)
        filename = f"{viatico.numero if viatico else 'viatico'}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


# Router principal que combina API + UI + extras
router = APIRouter()
router.include_router(router_api)
router.include_router(router_ui)
router.include_router(router_extra)
