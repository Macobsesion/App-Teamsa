"""Endpoints para wizard y vistas HTML de órdenes de compra."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from typing import Any

from app.web.jinja import get_templates
from sqlmodel import Session

from app.base.excepciones import RecursoNoEncontradoError
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import dp_usuario_actual
from app.rutas.permisos import para_modulo
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity

from app.modulos.proveedores.proveedores_modelo import Proveedor
from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra

router = APIRouter(prefix="/ui/ordenes-compra", tags=["Ordenes Compra - UI"])
TEMPLATES = get_templates()


@router.get("/wizard")
def mostrar_wizard_orden_compra(
    request: Request,
    id: int | None = None,
    db: Session = Depends(obtener_sesion_bd),
    usuario: Any = Depends(dp_usuario_actual),
):
    """Wizard para crear/editar orden de compra completa con proveedores."""
    # Validación dinámica de permisos usando la dependencia centralizada
    accion = "editar" if id else "crear"
    verificador = para_modulo("ordenes_compra", accion)
    
    # Ejecutamos la verificación manualmente si no queremos usarla como Dependencia de FastAPI
    # (aunque lo ideal es que sea un Depends en la firma, aquí lo hacemos así para mantener el flujo de id opcional)
    u_db = verificador(usuario, db)

    return TEMPLATES.TemplateResponse(
        "ui/ordenes_compra/wizard.html",
        {"request": request, "usuario": u_db}
    )


@router.get("/{orden_id}/detalle")
def ver_detalle_orden(
    orden_id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    usuario = Depends(para_modulo("ordenes_compra", "ver")),
):
    """Vista de detalle de una orden de compra."""
    from app.modulos.ordenes_compra.ordenes_compra_repositorio import RepositorioOrdenCompra
    repo = RepositorioOrdenCompra(db)
    orden = repo.obtener_por_id(orden_id)
    
    if not orden:
        raise RecursoNoEncontradoError("Orden de Compra no encontrada")
    
    # RBAC context for detail view
    perms_edit = getattr(usuario, "permisos_editar", []) or []
    perms_delete = getattr(usuario, "permisos_eliminar", []) or []
    
    puede_editar = "ordenes_compra" in perms_edit
    puede_eliminar = "ordenes_compra" in perms_delete

    return TEMPLATES.TemplateResponse(
        "ui/ordenes_compra/detalle.html",
        {
            "request": request,
            "usuario": usuario,
            "orden": orden,
            "proveedor": orden.proveedor, # Usamos la relación del modelo
            "detalles": orden.detalles,
            "puede_editar": puede_editar,
            "puede_eliminar": puede_eliminar,
        }
    )
