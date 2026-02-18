"""
Eventos y Handlers del módulo de Órdenes.
"""
from sqlmodel import Session
from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.cotizaciones.enums import EstadoCotizacion

# Constantes de Eventos
EVENTO_ORDEN_CREADA = "orden_creada"

def handler_actualizar_cotizacion_aceptada(payload: dict) -> None:
    """
    Handler que escucha cuando se crea una orden y actualiza la cotización a 'aceptada'.
    
    Payload esperado:
    {
        "orden_id": int,
        "cotizacion_id": int,
        "session_factory": Callable[[], Session] # Hack para obtener sesión en entorno síncrono
    }
    """
    orden_id = payload.get("orden_id")
    cotizacion_id = payload.get("cotizacion_id")
    session_factory = payload.get("session_factory")
    
    if not cotizacion_id or not session_factory:
        return

    # Crear una nueva sesión para este side-effect (o reusar si se pasara la sesión activa)
    # En este diseño simple, asumimos que obtenemos una nueva sesión para aislar la transacción
    with session_factory() as db:
        cotizacion = db.get(Cotizacion, cotizacion_id)
        if cotizacion and cotizacion.estado != EstadoCotizacion.PROGRAMADA.value:
            # Nota: Podríamos tener un estado 'aceptada', pero en el enum pusimos 'programada' como ejemplo
            # Vamos a usar 'programada' que es lo que tiene sentido con la OT
            cotizacion.estado = EstadoCotizacion.PROGRAMADA.value 
            db.add(cotizacion)
            db.commit()
            print(f"[EVENTO] Cotización {cotizacion_id} actualizada a PROGRAMADA por creación de Orden {orden_id}")
