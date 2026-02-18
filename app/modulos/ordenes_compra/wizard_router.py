"""Endpoints para wizard y vistas HTML de órdenes de compra."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app.base.excepciones import RecursoNoEncontradoError
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import exigir_roles, dp_usuario_actual
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity

from app.modulos.proveedores.proveedores_modelo import Proveedor
from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra

router = APIRouter(prefix="/ui/ordenes-compra", tags=["Ordenes Compra - UI"])
TEMPLATES = Jinja2Templates(directory="web/templates")


@router.get("/wizard")
def mostrar_wizard_orden_compra(
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(exigir_roles("admin", "compras")),
):
    """Wizard para crear/editar orden de compra completa con proveedores."""
    return TEMPLATES.TemplateResponse(
        "ui/ordenes_compra/wizard.html",
        {"request": request, "usuario": usuario}
    )


@router.get("/{orden_id}/detalle")
def ver_detalle_orden(
    orden_id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual),
):
    """Vista de detalle de una orden de compra."""
    orden = db.get(OrdenCompra, orden_id)
    if not orden:
        raise RecursoNoEncontradoError("Orden de Compra no encontrada")
    
    # Eager loading simulado (si no está configurado en relación lazy='joined')
    proveedor = db.get(Proveedor, orden.proveedor_id)
    
    return TEMPLATES.TemplateResponse(
        "ui/ordenes_compra/detalle.html",
        {
            "request": request,
            "usuario": usuario,
            "orden": orden,
            "proveedor": proveedor,
            "detalles": orden.detalles, # Relación ORM
        }
    )
