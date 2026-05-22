# Dependencias reutilizables para rutas (cookie-only).
#
# Aquí centralizamos la obtención de la sesión de base de datos y la identidad
# del usuario autenticado a partir del token JWT guardado en una cookie HTTPOnly.

from typing import Callable

from fastapi import Depends, HTTPException, Request, status  # type: ignore
from sqlmodel import Session  # type: ignore

from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.cls_identidad import TokenInvalidoError, obtener_gestor_identidad
from app.nucleo.sesion import obtener_token_cookie


dp_obtener_sesion_db = obtener_sesion_bd


def dp_usuario_actual(request: Request) -> UsuarioIdentity:
    # # Extrae el token de la cookie de sesión; si no existe, 401
    token = obtener_token_cookie(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        )
    try:
        # # Valida y decodifica el JWT devolviendo usuario y rol
        usuario, rol = obtener_gestor_identidad().extraer_identidad(token)
    except TokenInvalidoError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudieron validar las credenciales",
        ) from exc
    return UsuarioIdentity(usuario=usuario, rol=rol)


def dp_usuario_db(
    request: Request,
    db: Session = Depends(dp_obtener_sesion_db)
) -> Any:
    """Extrae la identidad del usuario y recupera su registro completo en la base de datos."""
    identidad = dp_usuario_actual(request)
    from app.modulos.usuarios.usuarios_modelo import Usuario
    from sqlmodel import select
    usuario = db.exec(select(Usuario).where(Usuario.usuario == identidad.usuario)).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado en el sistema",
        )
    return usuario



