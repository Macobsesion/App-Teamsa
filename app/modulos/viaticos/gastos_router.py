"""Endpoints para gestión de gastos en viáticos."""
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import exigir_roles
from app.modulos.viaticos.viaticos_esquemas import GastoCreate, GastoRead
from app.modulos.viaticos.viaticos_repositorio import RepositorioGasto
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity

router = APIRouter(prefix="/api/viaticos", tags=["Viáticos - Gastos"])


@router.post("/{viatico_id}/gastos", response_model=GastoRead)
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


@router.delete("/{viatico_id}/gastos/{gasto_id}")
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
