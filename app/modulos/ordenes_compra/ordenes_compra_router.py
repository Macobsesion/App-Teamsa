"""Router para Órdenes de Compra."""
from fastapi import APIRouter, Depends, Body, Response
from sqlmodel import Session
from typing import Any

from app.base.descriptor_crud import DescriptorCRUD, ConfiguracionUI
from app.base.factory_modulo import crear_modulo_crud_estandar
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import dp_usuario_actual
from app.rutas.permisos import para_modulo
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.base.excepciones import RecursoNoEncontradoError, ReglaNegocioError

from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra
from app.modulos.proveedores.proveedores_modelo import Proveedor
from app.modulos.servicios_proveedores.servicios_proveedores_modelo import ServicioProveedor
from app.modulos.ordenes_compra.ordenes_compra_esquemas import (
    OrdenCompraCreate, OrdenCompraUpdate, OrdenCompraRead, OrdenCompraWizardRead
)
from app.modulos.ordenes_compra.ordenes_compra_repositorio import RepositorioOrdenCompra
from app.modulos.ordenes_compra.ordenes_compra_servicios import ServicioCreacionOrdenCompra
from app.modulos.ordenes_compra.pdf_generator import generar_pdf_orden_compra
from app.modulos.ordenes_compra import wizard_router


# Router para endpoints custom (creación compleja)
router_extras = APIRouter(prefix="/api/ordenes-compra", tags=["Ordenes Compra - Extras"])

@router_extras.post("/completa", response_model=OrdenCompraRead)
def crear_orden_completa(
    datos: dict = Body(...),
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("ordenes_compra", "crear"))
):
    """Crea una orden de compra completa con detalles."""
    servicio = ServicioCreacionOrdenCompra(db)
    orden = servicio.crear_completa(datos, usuario.usuario)
    return orden


@router_extras.get("/{orden_id}/completa", response_model=OrdenCompraWizardRead)
def obtener_orden_completa(
    orden_id: int,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Retorna una orden de compra con sus detalles para modo edición."""
    orden = db.get(OrdenCompra, orden_id)
    if not orden:
        raise RecursoNoEncontradoError("Orden de compra no encontrada")

    return orden


@router_extras.put("/{orden_id}/actualizar-completa", response_model=OrdenCompraRead)
def actualizar_orden_completa(
    orden_id: int,
    datos: dict = Body(...),
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("ordenes_compra"))
):
    """Actualiza una orden de compra existente con todos sus detalles."""
    servicio = ServicioCreacionOrdenCompra(db)
    orden = servicio.actualizar_completa(orden_id, datos, usuario.usuario)
    return orden


@router_extras.patch("/{orden_id}/notas-privadas")
def actualizar_notas_privadas_oc(
    orden_id: int,
    data: dict,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(para_modulo("ordenes_compra")),
):
    """Actualiza las notas privadas de una orden de compra."""
    repo = RepositorioOrdenCompra(db)
    orden = db.get(OrdenCompra, orden_id)
    if not orden:
        raise RecursoNoEncontradoError("Orden de compra no encontrada")

    orden.actualizar_notas_privadas(data.get('notas_privadas'), usuario.usuario)
    return repo.guardar(orden)


@router_extras.get("/{orden_id}/pdf")
def descargar_pdf_orden(
    orden_id: int,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Genera y descarga el PDF de una orden de compra."""
    pdf_bytes = generar_pdf_orden_compra(orden_id, db)
    orden = db.get(OrdenCompra, orden_id)
    if not orden:
        raise RecursoNoEncontradoError("Orden de compra no encontrada")
    filename = f"OC-{orden.folio}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"},
    )


# Descriptor CRUD estándar
descriptor = DescriptorCRUD[
    RepositorioOrdenCompra,
    OrdenCompraCreate,
    OrdenCompraUpdate,
    OrdenCompraRead,
    UsuarioIdentity
](
    label="Órdenes de Compra",
    base_url="/api/ordenes-compra",
    repo_factory=RepositorioOrdenCompra,
    schema_read=OrdenCompraRead,
    schema_create=OrdenCompraCreate,
    schema_update=OrdenCompraUpdate,
    config_ui=ConfiguracionUI(
        topic="ordenes_compra",
        columnas_incluir=["folio", "fecha_emision", "proveedor_id", "estado", "total"],
        columnas_excluir={"creado_por", "modificado_por"},
        boton_crear={"texto": "📦 Nueva Orden de Compra", "url": "/ui/ordenes-compra/wizard", "modal": False},
    )
)

# Router combinado
router = crear_modulo_crud_estandar(
    descriptor=descriptor,
    nombre_modulo="ordenes_compra",
    routers_prioritarios=[router_extras, wizard_router.router]
)
