# Servicios de autenticación (hash de contraseñas y emisión de tokens JWT).

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

from jose import jwt  # type: ignore
from passlib.context import CryptContext  # type: ignore

from .configuracion import settings


class GestorAutenticacion:
    """Encapsula la lógica de credenciales (hash + emisión de tokens)."""

    def __init__(self, *, clave_secreta: str, algoritmo: str, minutos_expira: int):
        # Parámetros inmutables del gestor; permiten reutilizar la misma instancia.
        self._clave_secreta = clave_secreta
        self._algoritmo = algoritmo
        self._minutos_expira = minutos_expira
        # Contexto de passlib configurado con bcrypt para crear/verificar hashes.
        self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verificar_contrasena(self, contrasena_plana: str, contrasena_hasheada: str) -> bool:
        # Compara una contraseña enviada por el usuario contra el hash guardado.
        return self._ctx.verify(contrasena_plana, contrasena_hasheada)

    def obtener_hash_contrasena(self, contrasena: str) -> str:
        # Genera un hash seguro (bcrypt) para persistir en la base de datos.
        return self._ctx.hash(contrasena)

    def crear_token_acceso(self, datos: dict[str, Any]) -> str:
        # Clona los datos, agrega expiración y firma el JWT con la configuración actual.
        a_codificar = datos.copy()
        expiracion = datetime.now(timezone.utc) + timedelta(minutes=self._minutos_expira)
        a_codificar.update({"exp": expiracion})
        return jwt.encode(a_codificar, self._clave_secreta, algorithm=self._algoritmo)


@lru_cache
def obtener_gestor_autenticacion() -> GestorAutenticacion:
    """Devuelve una instancia reutilizable configurada desde variables de entorno."""
    # `lru_cache` memoriza el resultado para que la creación del gestor sea única
    # por proceso; FastAPI y los scripts reutilizan así el mismo objeto.
    return GestorAutenticacion(
        clave_secreta=settings.SECRET_KEY,
        algoritmo=settings.ALGORITHM,
        minutos_expira=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
