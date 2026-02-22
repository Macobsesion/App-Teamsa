"""
Eventos y Handlers del módulo de Órdenes.
"""
from sqlmodel import Session
from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.cotizaciones.enums import EstadoCotizacion
from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo

# Constantes de Eventos
EVENTO_ORDEN_CREADA = "orden_creada"
EVENTO_ORDEN_FINALIZADA = "orden_finalizada"
EVENTO_ORDEN_CANCELADA = "orden_cancelada"

def handler_actualizar_cotizacion_aceptada(payload: dict) -> None:
    """Handler que escucha cuando se crea una orden y actualiza la cotización a 'programada'."""
    orden_id = payload.get("orden_id")
    cotizacion_id = payload.get("cotizacion_id")
    db = payload.get("session_actual")
    
    if not cotizacion_id or not db: return

    cotizacion = db.get(Cotizacion, cotizacion_id)
    if cotizacion and cotizacion.estado != EstadoCotizacion.PROGRAMADA.value:
        cotizacion.estado = EstadoCotizacion.PROGRAMADA.value 
        db.add(cotizacion)
        db.commit()

def handler_cotizacion_finalizada(payload: dict) -> None:
    """Handler para cuando una OT se finaliza: la cotización pasa a finalizada (si aplica)."""
    cotizacion_id = payload.get("cotizacion_id")
    db = payload.get("session_actual")
    
    if not cotizacion_id or not db: return

    cotizacion = db.get(Cotizacion, cotizacion_id)
    if cotizacion and cotizacion.estado != EstadoCotizacion.FINALIZADA.value:
        cotizacion.estado = EstadoCotizacion.FINALIZADA.value
        db.add(cotizacion)
        db.commit()

def handler_cotizacion_revertir_a_enviada(payload: dict) -> None:
    """
    Handler para cuando una OT se cancela: verifica si la cotización no tiene más OTs activas.
    Si todas las OTs están canceladas, la cotización regresa a 'enviada'.
    """
    from sqlmodel import select
    cotizacion_id = payload.get("cotizacion_id")
    db = payload.get("session_actual")
    
    if not cotizacion_id or not db: return

    # Buscar si existen OTs para esta cotización que NO estén canceladas
    ots_activas = db.exec(
        select(OrdenTrabajo)
        .where(OrdenTrabajo.cotizacion_id == cotizacion_id)
        .where(OrdenTrabajo.estado != "cancelada")
    ).first()

    # Si no hay OTs activas, regresar cotización a enviada
    if not ots_activas:
        cotizacion = db.get(Cotizacion, cotizacion_id)
        if cotizacion and cotizacion.estado == EstadoCotizacion.PROGRAMADA.value:
            cotizacion.estado = EstadoCotizacion.ENVIADA.value
            db.add(cotizacion)
            db.commit()
