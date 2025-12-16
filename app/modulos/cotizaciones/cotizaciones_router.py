"""Router y descriptor CRUD para cotizaciones con endpoint de PDF."""
from typing import Any
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request  # type: ignore
from fastapi.responses import Response  # type: ignore
from sqlmodel import Session  # type: ignore

from app.base.descriptor_crud import DescriptorCRUD
from app.base.ui_crud import DescriptorUI, construir_enrutador_ui
from app.nucleo.base_datos import obtener_sesion_bd, obtener_motor
from app.rutas.dependencias import exigir_roles, dp_usuario_actual
from app.modulos.cotizaciones.cotizaciones_esquemas import (
    CotizacionRead,
    CotizacionCreate,
    CotizacionUpdate,
    ConceptoCreate,
    ConceptoRead,
)
from app.modulos.cotizaciones.cotizaciones_repositorio import (
    RepositorioCotizacion,
    RepositorioConcepto,
)
from app.modulos.cotizaciones.pdf_generator import generar_pdf_cotizacion
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity


def _factory(db: Session) -> RepositorioCotizacion:
    return RepositorioCotizacion(db)


def _campos_creacion(payload: CotizacionCreate, actor: UsuarioIdentity) -> dict[str, Any]:
    """Genera campos adicionales al crear una cotización."""
    # Crear repo temporal para generar número
    with Session(obtener_motor()) as db:
        repo_temp = RepositorioCotizacion(db)
        numero = repo_temp.generar_siguiente_numero()
        fecha_vigencia = repo_temp.calcular_fecha_vigencia(date.today())
    
    return {
        "numero": numero,
        "fecha_emision": date.today(),
        "fecha_vigencia": fecha_vigencia,
        "creado_por": actor.usuario,
        "modificado_por": actor.usuario,
    }


def _campos_actualizacion(payload: CotizacionUpdate, actor: UsuarioIdentity) -> dict[str, Any]:
    return {"modificado_por": actor.usuario}


# Descriptor declarativo del módulo
descriptor = DescriptorCRUD[RepositorioCotizacion, CotizacionCreate, CotizacionUpdate, CotizacionRead, UsuarioIdentity](
    label="Cotizaciones",
    base_url="/api/cotizaciones",
    repo_factory=_factory,
    schema_read=CotizacionRead,
    schema_create=CotizacionCreate,
    schema_update=CotizacionUpdate,
    campos_editables={
        "cliente_id", "peticion", "estado", "notas", "condiciones_pago"
    },
    campos_creacion_extra=_campos_creacion,
    campos_actualizacion_extra=_campos_actualizacion,
    filtros_permitidos={"estado", "cliente_id"},
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
    prefix="/ui/cotizaciones",
    repo_factory=_factory,
    schema_create=CotizacionCreate,
    schema_update=CotizacionUpdate,
    hooks=descriptor.build_hooks(),
    obtener_sesion=obtener_sesion_bd,
    list_dependencies=[Depends(dp_usuario_actual)],
    write_dependency=exigir_roles("admin"),
    ui=DescriptorUI(
        tpl_filas="ui/cotizaciones/_filas.html",
        tpl_form="ui/cotizaciones/_form.html",
    ),
    label=descriptor.label,
    actor_dependency=dp_usuario_actual,
    columnas=descriptor.frontend_config().get("columnas"),
    campo_busqueda=descriptor.campo_busqueda,
)

# Router extra para vistas HTML adicionales y conceptos
router_extra_ui = APIRouter(prefix="/ui/cotizaciones", tags=["Cotizaciones UI"])


@router_extra_ui.get("/wizard")
def mostrar_wizard_cotizacion(
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """Wizard para crear cotización completa."""
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="web/templates")
    
    return templates.TemplateResponse(
        "ui/cotizaciones/wizard.html",
        {
            "request": request,
            "usuario": usuario,
        }
    )


@router_extra_ui.get("/{cotizacion_id}/detalle")
def ver_detalle_cotizacion(
    cotizacion_id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual),
):
    """Vista de detalle de una cotización con gestión de conceptos."""
    from fastapi.templating import Jinja2Templates
    from app.modulos.clientes.clientes_modelo import Cliente
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    
    templates = Jinja2Templates(directory="web/templates")
    
    # Obtener cotización
    repo = RepositorioCotizacion(db)
    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotizacion no encontrada")
    
    # Obtener cliente
    cliente = db.get(Cliente, cotizacion.cliente_id)
    
    # Obtener conceptos
    conceptos = repo.obtener_conceptos(cotizacion_id)
    
    return templates.TemplateResponse(
        "ui/cotizaciones/detalle.html",
        {
            "request": request,
            "usuario": usuario,
            "cotizacion": cotizacion,
            "cliente": cliente,
            "conceptos": conceptos,
        }
    )


@router_extra_ui.get("/{cotizacion_id}/concepto-form")
def mostrar_formulario_concepto(
    cotizacion_id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(dp_usuario_actual),
):
    """Formulario para agregar concepto (modal HTMX)."""
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="web/templates")
    
    return templates.TemplateResponse(
        "ui/cotizaciones/_concepto_form.html",
        {
            "request": request,
            "cotizacion_id": cotizacion_id,
        }
    )


@router_extra_ui.post("/{cotizacion_id}/conceptos")
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
    _usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
    descuento_porcentaje: float = 0.0,
):
    """Agrega concepto y devuelve lista actualizada (HTMX)."""
    from fastapi.templating import Jinja2Templates
    from decimal import Decimal
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    
    templates = Jinja2Templates(directory="web/templates")
    
    # Agregar concepto
    repo_concepto = RepositorioConcepto(db)
    repo_concepto.crear(
        cotizacion_id=cotizacion_id,
        servicio_id=servicio_id,
        codigo_sat=codigo_sat,
        descripcion=descripcion,
        unidad=unidad,
        cantidad=Decimal(str(cantidad)),
        precio_unitario=Decimal(str(precio_unitario)),
        descuento_porcentaje=Decimal(str(descuento_porcentaje)),
    )
    
    # Obtener datos actualizados
    repo = RepositorioCotizacion(db)
    cotizacion = db.get(Cotizacion, cotizacion_id)
    conceptos = repo.obtener_conceptos(cotizacion_id)
    
    # Devolver lista actualizada
    return templates.TemplateResponse(
        "ui/cotizaciones/_conceptos_list.html",
        {
            "request": request,
            "cotizacion": cotizacion,
            "conceptos": conceptos,
        }
    )


@router_extra_ui.delete("/{cotizacion_id}/conceptos/{concepto_id}")
def eliminar_concepto_htmx(
    cotizacion_id: int,
    concepto_id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """Elimina concepto y devuelve lista actualizada (HTMX)."""
    from fastapi.templating import Jinja2Templates
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    
    templates = Jinja2Templates(directory="web/templates")
    
    # Eliminar concepto
    repo_concepto = RepositorioConcepto(db)
    repo_concepto.eliminar(concepto_id, cotizacion_id)
    
    # Obtener datos actualizados
    repo = RepositorioCotizacion(db)
    cotizacion = db.get(Cotizacion, cotizacion_id)
    conceptos = repo.obtener_conceptos(cotizacion_id)
    
    # Devolver lista actualizada
    return templates.TemplateResponse(
        "ui/cotizaciones/_conceptos_list.html",
        {
            "request": request,
            "cotizacion": cotizacion,
            "conceptos": conceptos,
        }
    )


# Router adicional para API de conceptos y PDF
router_extra_api = APIRouter(prefix="/api/cotizaciones", tags=["Cotizaciones"])


@router_extra_api.post("/{cotizacion_id}/conceptos", response_model=ConceptoRead)
def agregar_concepto_api(
    cotizacion_id: int,
    concepto: ConceptoCreate,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """Agrega un concepto a una cotización y recalcula totales (API JSON)."""
    repo = RepositorioConcepto(db)
    return repo.crear(
        cotizacion_id=cotizacion_id,
        servicio_id=concepto.servicio_id,
        codigo_sat=concepto.codigo_sat,
        descripcion=concepto.descripcion,
        unidad=concepto.unidad,
        cantidad=concepto.cantidad,
        precio_unitario=concepto.precio_unitario,
    )


@router_extra_api.delete("/{cotizacion_id}/conceptos/{concepto_id}")
def eliminar_concepto_api(
    cotizacion_id: int,
    concepto_id: int,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """Elimina un concepto de una cotización y recalcula totales (API JSON)."""
    repo = RepositorioConcepto(db)
    repo.eliminar(concepto_id, cotizacion_id)
    return {"detail": "Concepto eliminado"}


@router_extra_api.post("/crear-completa")
def crear_cotizacion_completa(
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """Crea una cotización completa con conceptos en una sola transacción."""
    from datetime import date, timedelta
    from decimal import Decimal
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    
    # Generar número de cotización
    repo = RepositorioCotizacion(db)
    numero = repo.generar_siguiente_numero()
    fecha_emision = date.today()
    fecha_vigencia = repo.calcular_fecha_vigencia(fecha_emision)
    
    # Crear cotización
    cotizacion = Cotizacion(
        numero=numero,
        cliente_id=data['cliente_id'],
        estado='borrador',
        metodo_pago=data.get('metodo_pago', 'Por confirmar'),
        forma_pago=data.get('forma_pago', '99'),
        notas=data.get('notas'),
        fecha_emision=fecha_emision,
        fecha_vigencia=fecha_vigencia,
        creado_por=usuario.usuario,
        modificado_por=usuario.usuario,
    )
    
    db.add(cotizacion)
    db.flush()  # Para obtener el ID
    
    # Agregar conceptos
    repo_concepto = RepositorioConcepto(db)
    for servicio_data in data.get('servicios', []):
        repo_concepto.crear(
            cotizacion_id=cotizacion.id,
            servicio_id=servicio_data['servicio_id'],
            codigo_sat=servicio_data['codigo_sat'],
            descripcion=servicio_data['descripcion'],
            unidad=servicio_data['unidad'],
            cantidad=Decimal(str(servicio_data['cantidad'])),
            precio_unitario=Decimal(str(servicio_data['precio_unitario'])),
            descuento_porcentaje=Decimal(str(servicio_data.get('descuento_porcentaje', 0))),
        )
    
    db.commit()
    db.refresh(cotizacion)
    
    return {"id": cotizacion.id, "numero": cotizacion.numero}


@router_extra_api.get("/{cotizacion_id}/pdf")
def descargar_pdf(
    cotizacion_id: int,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(dp_usuario_actual),
):
    """Genera y descarga el PDF de una cotización."""
    try:
        pdf_bytes = generar_pdf_cotizacion(cotizacion_id, db)
        
        # Obtener número de cotización para el filename
        from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
        cotizacion = db.get(Cotizacion, cotizacion_id)
        filename = f"{cotizacion.numero if cotizacion else 'cotizacion'}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"'
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
router.include_router(router_extra_ui)
router.include_router(router_extra_api)
