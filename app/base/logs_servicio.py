import logging
from sqlmodel import Session
from app.base.logs_modelo import LogActividad

logger = logging.getLogger("teamsa.logs")

class ServicioLogs:
    @staticmethod
    def registrar(usuario: str, accion: str, modulo: str, detalles: str = None, ip: str = None):
        """
        Registra una actividad en la base de datos de forma independiente.
        Utiliza su propia sesión para evitar interferir con la transacción principal
        y asegurar que el log se guarde incluso si la operación principal falla.
        """
        from app.nucleo.base_datos import obtener_motor
        
        try:
            logger.debug(f"Registrando {accion} en {modulo} por {usuario}")
            with Session(obtener_motor()) as db:
                log = LogActividad(
                    usuario=usuario,
                    accion=accion,
                    modulo=modulo,
                    detalles=detalles,
                    ip=ip
                )
                db.add(log)
                db.commit()
        except Exception as e:
            # Silenciamos el error para no bloquear la UX, solo registramos en consola
            logger.warning(f"Error al registrar log de actividad: {e}")
