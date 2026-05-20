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

def handler_cotizacion_a_programada(payload: dict) -> None:
    """Handler que escucha cuando se crea una orden y actualiza la cotización a 'programada'."""
    import logging
    logger = logging.getLogger("teamsa")
    
    cotizacion_id = payload.get("cotizacion_id")
    db = payload.get("session_actual")
    
    logger.info(f"EVENTO: Procesando actualización de cotización {cotizacion_id} tras creación de OT")
    
    if not cotizacion_id or not db: 
        logger.warning("EVENTO: No se recibió cotizacion_id o session_actual en el payload")
        return

    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    from app.modulos.cotizaciones.enums import EstadoCotizacion

    cotizacion = db.get(Cotizacion, cotizacion_id)
    if cotizacion:
        logger.info(f"EVENTO: Estado actual de cotización {cotizacion.id}: {cotizacion.estado}")
        if cotizacion.estado != EstadoCotizacion.PROGRAMADA.value:
            cotizacion.estado = EstadoCotizacion.PROGRAMADA.value 
            db.add(cotizacion)
            db.flush()
            logger.info(f"EVENTO: Cotización {cotizacion_id} actualizada a 'programada'")
    else:
        logger.error(f"EVENTO: No se encontró la cotización {cotizacion_id} en la base de datos")

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
    query_activas = select(OrdenTrabajo).where(
        and_(
            OrdenTrabajo.cotizacion_id == cotizacion_id,
            OrdenTrabajo.estado != "cancelada"
        )
    )
    ots_activas = db.exec(query_activas).all()

    if not ots_activas:
        # No queda nada activo -> Regresa al origen
        if cotizacion.estado != EstadoCotizacion.EMITIDA.value:
            cotizacion.estado = EstadoCotizacion.EMITIDA.value
            db.add(cotizacion)
    else:
        # Quedan OTs activas. ¿Están todas finalizadas?
        query_pendientes = select(OrdenTrabajo).where(
            and_(
                OrdenTrabajo.cotizacion_id == cotizacion_id,
                OrdenTrabajo.estado != "finalizada",
                OrdenTrabajo.estado != "cancelada"
            )
        )
        pendientes = db.exec(query_pendientes).all()
        
        if pendientes:
            # Hay trabajo pendiente -> Debe estar en PROGRAMADA
            if cotizacion.estado != EstadoCotizacion.PROGRAMADA.value:
                cotizacion.estado = EstadoCotizacion.PROGRAMADA.value
                db.add(cotizacion)
        else:
            # Todas las activas están finalizadas -> Debe estar en FINALIZADA
            if cotizacion.estado != EstadoCotizacion.FINALIZADA.value:
                cotizacion.estado = EstadoCotizacion.FINALIZADA.value
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
        if evento == EVENTO_ORDEN_CANCELADA:
            # Revertir a borrador para que sea editable o eliminable
            if v.estado != EstadoViatico.CANCELADO.value and v.estado != EstadoViatico.FINALIZADO.value:
                v.estado = EstadoViatico.BORRADOR.value
                v.modificado_por = "sistema (cancelación OT)"
        
        db.add(v)
    db.flush()
