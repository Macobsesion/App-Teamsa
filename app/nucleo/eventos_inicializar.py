from app.base.eventos import BusEventos
from app.modulos.ordenes_trabajo.eventos import (
    EVENTO_ORDEN_CREADA, 
    EVENTO_ORDEN_CANCELADA,
    EVENTO_ORDEN_FINALIZADA,
    handler_actualizar_cotizacion_aceptada,
    handler_cotizacion_revertir_a_emitida,
    handler_cotizacion_finalizada
)

def registrar_eventos_globales():
    """Suscribe todos los handlers de negocio a sus respectivos eventos."""
    
    # 1. Órdenes de Trabajo -> Cotizaciones
    BusEventos.suscribir(EVENTO_ORDEN_CREADA, handler_actualizar_cotizacion_aceptada)
    BusEventos.suscribir(EVENTO_ORDEN_CANCELADA, handler_cotizacion_revertir_a_emitida)
    BusEventos.suscribir(EVENTO_ORDEN_FINALIZADA, handler_cotizacion_finalizada)
    
    # 2. Órdenes de Trabajo -> Viáticos
    from app.modulos.ordenes_trabajo.eventos import handler_sincronizar_viaticos_desde_ot
    BusEventos.suscribir(EVENTO_ORDEN_CREADA, handler_sincronizar_viaticos_desde_ot)
    BusEventos.suscribir(EVENTO_ORDEN_CANCELADA, handler_sincronizar_viaticos_desde_ot)
    
    # Aquí se pueden registrar más eventos de otros módulos si es necesario
