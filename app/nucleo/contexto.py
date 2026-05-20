from contextvars import ContextVar
from typing import Optional

# Variable de contexto para almacenar la identidad del usuario en el hilo de ejecución actual.
# Esto permite que la capa de base de datos (SQLAlchemy) acceda al usuario sin pasarlo por todos los métodos.
contexto_usuario: ContextVar[Optional[str]] = ContextVar("contexto_usuario", default=None)

def establecer_usuario_actual(usuario: Optional[str]) -> None:
    contexto_usuario.set(usuario)

def obtener_usuario_actual() -> Optional[str]:
    return contexto_usuario.get()
