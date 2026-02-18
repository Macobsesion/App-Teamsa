"""
Sistema de Eventos de Dominio (Observer Pattern).
Permite desacoplar efectos secundarios mediante publicación/suscripción.
"""
from collections import defaultdict
from typing import Any, Callable, List

# Definición de tipos para handlers
# Un handler recibe el payload del evento y (opcionalmente) dependencias inyectadas si se compleijza
EventHandler = Callable[[Any], None]

class BusEventos:
    """Bus de eventos simple (Singleton-ish)."""
    
    _suscriptores: dict[str, List[EventHandler]] = defaultdict(list)

    @classmethod
    def suscribir(cls, evento: str, handler: EventHandler) -> None:
        """Registra un handler para un tipo de evento."""
        cls._suscriptores[evento].append(handler)

    @classmethod
    def publicar(cls, evento: str, payload: Any) -> None:
        """
        Publica un evento y ejecuta sincronamente todos los handlers suscritos.
        
        Nota: En un sistema más complejo, esto podría usar colas de tareas (Celery/Redis)
        para ejecución asíncrona.
        """
        if evento in cls._suscriptores:
            for handler in cls._suscriptores[evento]:
                try:
                    handler(payload)
                except Exception as e:
                    # Loguear error pero no detener flujos principales si es posible
                    print(f"Error en handler de evento {evento}: {e}")

    @classmethod
    def limpiar(cls) -> None:
        """Limpia todos los suscriptores (útil para tests)."""
        cls._suscriptores.clear()
