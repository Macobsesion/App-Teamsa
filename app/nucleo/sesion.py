from fastapi import Request, Response  # type: ignore
from .configuracion import settings

# Helpers de sesión (cookie HTTPOnly) centralizados.

def obtener_token_cookie(request: Request) -> str | None:
    return request.cookies.get(settings.ACCESS_COOKIE_NAME)


def establecer_cookie_sesion(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=True,  # Cambiado a True para HTTPS
        samesite="lax",
        path="/",
    )


def eliminar_cookie_sesion(response: Response) -> None:
    """Elimina la cookie de sesión del cliente."""
    response.delete_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        path="/",
        secure=True,
        samesite="lax"
    )
