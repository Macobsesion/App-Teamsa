"""
Sistema de Eventos de Dominio (Observer Pattern).
Permite desacoplar efectos secundarios mediante publicación/suscripción.
"""
import logging
from collections import defaultdict
from typing import Any, Callable, List

logger = logging.getLogger("teamsa")

# Definición de tipos para handlers
EventHandler = Callable[[Any], None]


class BusEventos:
    """Bus de eventos simple (Singleton-ish)."""

    _suscriptores: dict[str, List[EventHandler]] = defaultdict(list)

    @classmethod
    def suscribir(cls, evento: str, handler: EventHandler) -> None:
        """Registra un handler para un tipo de evento (idempotente: ignora duplicados)."""
        if handler not in cls._suscriptores[evento]:
            cls._suscriptores[evento].append(handler)

    @classmethod
    def publicar(cls, evento: str, payload: Any) -> None:
        """
        Publica un evento y ejecuta sincronamente todos los handlers suscritos.

        Nota: En un sistema más complejo, esto podría usar colas de tareas (Celery/Redis)
        para ejecución asíncrona.
        """
        for handler in cls._suscriptores.get(evento, []):
            try:
                handler(payload)
            except Exception:
                logger.exception("Error en handler de evento '%s'", evento)

    @classmethod
    def limpiar(cls) -> None:
        """Limpia todos los suscriptores (útil para tests)."""
        cls._suscriptores.clear()

