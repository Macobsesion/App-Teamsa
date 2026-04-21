"""
Eventos y Handlers del módulo de Órdenes.
"""
from sqlmodel import Session
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.cotizaciones.enums import EstadoCotizacion
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo

# Constantes de Eventos
EVENTO_ORDEN_CREADA = "orden_creada"
EVENTO_ORDEN_FINALIZADA = "orden_finalizada"
EVENTO_ORDEN_CANCELADA = "orden_cancelada"

def handler_actualizar_cotizacion_aceptada(payload: dict) -> None:
    """Handler que escucha cuando se crea una orden y actualiza la cotización a 'programada'."""
    cotizacion_id = payload.get("cotizacion_id")
    db = payload.get("session_actual")
    
    if not cotizacion_id or not db: return

    cotizacion = db.get(Cotizacion, cotizacion_id)
    if cotizacion and cotizacion.estado != EstadoCotizacion.PROGRAMADA.value:
        cotizacion.estado = EstadoCotizacion.PROGRAMADA.value 
        db.add(cotizacion)
        db.flush() # Usamos flush para permitir que otros handlers vean el cambio en la misma transacción

def handler_cotizacion_finalizada(payload: dict) -> None:
    """Handler para cuando una OT se finaliza: la cotización pasa a finalizada (si aplica)."""
    cotizacion_id = payload.get("cotizacion_id")
    db = payload.get("session_actual")
    
    if not cotizacion_id or not db: return

    from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
    from sqlmodel import select, and_

    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion: return

    # Verificar si quedan OTs pendientes
    query = select(OrdenTrabajo).where(
        and_(
            OrdenTrabajo.cotizacion_id == cotizacion_id,
            OrdenTrabajo.estado != "finalizada",
            OrdenTrabajo.estado != "cancelada"
        )
    )
    pendientes = db.exec(query).all()

    if not pendientes and cotizacion.estado != EstadoCotizacion.FINALIZADA.value:
        cotizacion.estado = EstadoCotizacion.FINALIZADA.value
        db.add(cotizacion)
        db.flush()

def handler_cotizacion_revertir_a_emitida(payload: dict) -> None:
    """
    Handler para cuando una OT se cancela: verifica si todas las OTs están canceladas, 
    la cotización regresa a 'emitida'.
    """
    cotizacion_id = payload.get("cotizacion_id")
    db = payload.get("session_actual")
    
    if not cotizacion_id or not db: return

    from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
    from sqlmodel import select, and_

    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion: return

    # Buscar OTs activas (no canceladas)
    query = select(OrdenTrabajo).where(
        and_(
            OrdenTrabajo.cotizacion_id == cotizacion_id,
            OrdenTrabajo.estado != "cancelada"
        )
    )
    ots_activas = db.exec(query).all()

    # Si no hay OTs activas, regresar cotización a emitida
    if not ots_activas:
        if cotizacion.estado != EstadoCotizacion.EMITIDA.value:
            cotizacion.estado = EstadoCotizacion.EMITIDA.value
            db.add(cotizacion)
            db.flush()

def handler_sincronizar_viaticos_desde_ot(payload: dict) -> None:
    """
    Handler que sincroniza el estado de los viáticos vinculados a una OT.
    - OT Creada -> Viáticos vinculados pasan a APROBADO (si tienen fecha).
    - OT Cancelada -> Viáticos vinculados regresan a BORRADOR.
    """
    orden_id = payload.get("orden_id")
    evento = payload.get("evento_tipo")
    db = payload.get("session_actual")
    
    if not orden_id or not db: return

    from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
    from app.modulos.viaticos.enums import EstadoViatico
    
    orden = db.get(OrdenTrabajo, orden_id)
    if not orden or not orden.viaticos: return

    for v in orden.viaticos:
        if evento == EVENTO_ORDEN_CREADA:
            if v.estado == EstadoViatico.BORRADOR.value:
                v.estado = EstadoViatico.APROBADO.value
        elif evento == EVENTO_ORDEN_CANCELADA:
            # Solo revertir si no tiene otras OTs activas
            v.estado = EstadoViatico.BORRADOR.value
        
        db.add(v)
    db.flush()
