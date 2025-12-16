# Validación de tokens JWT y extracción de identidad de usuario.
from functools import lru_cache
from typing import Tuple

from jose import JWTError, jwt  # type: ignore

from .configuracion import settings


class TokenInvalidoError(Exception):
    # Se lanza cuando el token no puede validarse (formato/expiración/claims).
    pass


class GestorIdentidad:
    def __init__(self, *, clave_secreta: str, algoritmo: str):
        self._clave_secreta = clave_secreta
        self._algoritmo = algoritmo

    def extraer_identidad(self, token: str) -> Tuple[str, str]:
        try:
            payload = jwt.decode(token, self._clave_secreta, algorithms=[self._algoritmo])
        except JWTError as exc:
            raise TokenInvalidoError("Token inválido o expirado") from exc

        username = payload.get("sub")
        rol = payload.get("rol")
        if not username or not rol:
            raise TokenInvalidoError("Token sin información de usuario o rol")
        return username, rol


@lru_cache
def obtener_gestor_identidad() -> GestorIdentidad:
    """Instancia única para validar JWT emitidos por la aplicación."""
    return GestorIdentidad(
        clave_secreta=settings.SECRET_KEY,
        algoritmo=settings.ALGORITHM,
    )
