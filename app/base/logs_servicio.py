from sqlmodel import Session
from app.base.logs_modelo import LogActividad

class ServicioLogs:
    @staticmethod
    def registrar(db: Session, usuario: str, accion: str, modulo: str, detalles: str = None, ip: str = None):
        """Registra una actividad en la base de datos."""
        try:
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
            # No queremos que un fallo en el log bloquee la operación principal
            print(f"Error al registrar log de actividad: {e}")
            db.rollback()
