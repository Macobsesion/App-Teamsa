"""Router para Órdenes de Compra."""
from fastapi import APIRouter, Depends, Body, HTTPException, Response
from sqlmodel import Session
from typing import Any

from app.base.descriptor_crud import DescriptorCRUD
from app.base.factory_modulo import crear_modulo_crud
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import exigir_roles, dp_usuario_actual
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity

from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra
from app.modulos.proveedores.proveedores_modelo import Proveedor
from app.modulos.servicios_proveedores.servicios_proveedores_modelo import ServicioProveedor
from app.modulos.ordenes_compra.ordenes_compra_esquemas import OrdenCompraCreate, OrdenCompraUpdate, OrdenCompraRead
from app.modulos.ordenes_compra.ordenes_compra_repositorio import RepositorioOrdenCompra
from app.modulos.ordenes_compra.ordenes_compra_servicios import ServicioCreacionOrdenCompra


# Router para endpoints custom (creación compleja)
router_extras = APIRouter(prefix="/api/ordenes-compra", tags=["Ordenes Compra - Extras"])

@router_extras.post("/completa", response_model=OrdenCompraRead)
def crear_orden_completa(
    datos: dict = Body(...),
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(exigir_roles("admin", "compras"))
):
    """Crea una orden de compra completa con detalles."""
    servicio = ServicioCreacionOrdenCompra(db)
    orden = servicio.crear_completa(datos, usuario.usuario)
    return orden


@router_extras.get("/{orden_id}/completa")
def obtener_orden_completa(
    orden_id: int,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Retorna una orden de compra con sus detalles para modo edición."""
    from app.base.excepciones import RecursoNoEncontradoError

    orden = db.get(OrdenCompra, orden_id)
    if not orden:
        raise RecursoNoEncontradoError("Orden de compra no encontrada")

    return {
        "id": orden.id,
        "folio": orden.folio,
        "proveedor_id": orden.proveedor_id,
        "fecha_emision": str(orden.fecha_emision),
        "fecha_entrega": str(orden.fecha_entrega_estimada) if orden.fecha_entrega_estimada else "",
        "metodo_pago": orden.metodo_pago,
        "forma_pago": orden.forma_pago,
        "notas": orden.notas or "",
        "estado": orden.estado,
        "items": [
            {
                "servicio_id": d.servicio_proveedor_id,
                "codigo": d.codigo_sku,
                "descripcion": d.descripcion,
                "unidad": d.unidad,
                "cantidad": float(d.cantidad),
                "precio_unitario": float(d.precio_unitario),
            }
            for d in orden.detalles
        ]
    }


@router_extras.put("/{orden_id}/actualizar-completa", response_model=OrdenCompraRead)
def actualizar_orden_completa(
    orden_id: int,
    datos: dict = Body(...),
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(exigir_roles("admin", "compras"))
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
    usuario: UsuarioIdentity = Depends(exigir_roles("admin", "compras")),
):
    """Actualiza las notas privadas de una orden de compra."""
    from app.base.excepciones import RecursoNoEncontradoError

    orden = db.get(OrdenCompra, orden_id)
    if not orden:
        raise RecursoNoEncontradoError("Orden de compra no encontrada")

    orden.notas_privadas = data.get('notas_privadas')
    orden.modificado_por = usuario.usuario
    db.commit()
    db.refresh(orden)
    return {"detail": "Notas privadas actualizadas", "notas_privadas": orden.notas_privadas}


@router_extras.get("/{orden_id}/pdf")
def descargar_pdf_orden(
    orden_id: int,
    db: Session = Depends(obtener_sesion_bd),
    usuario: UsuarioIdentity = Depends(dp_usuario_actual)
):
    """Genera y descarga el PDF de una orden de compra."""
    from app.modulos.ordenes_compra.pdf_generator import generar_pdf_orden_compra
    
    try:
        pdf_bytes = generar_pdf_orden_compra(orden_id, db)
        
        # Recuperar folio para el nombre del archivo (podríamos devolverlo desde la función, pero query simple es barato)
        # O mejor, mover la logica de response aqui.
        orden = db.get(OrdenCompra, orden_id) # Re-get is cheap or cached
        filename = f"OC-{orden.folio}.pdf"
        
        headers = {
            "Content-Disposition": f"inline; filename={filename}"
        }
        
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))


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
    columnas_incluir=["folio", "fecha_emision", "proveedor_id", "estado", "total"],
    columnas_excluir={"creado_por", "modificado_por"},
    topic="ordenes_compra",
    boton_crear={"texto": "📦 Nueva Orden de Compra", "url": "/ui/ordenes-compra/wizard", "modal": False},
)

# Router combinado
router = crear_modulo_crud(
    descriptor=descriptor,
    obtener_sesion=obtener_sesion_bd,
    actor_dependency=dp_usuario_actual,
    write_dependency=exigir_roles("admin", "compras"),
    tpl_filas="ui/ordenes_compra/_filas.html",
    tpl_form="ui/ordenes_compra/_form.html",
    routers_adicionales=[router_extras]
)
