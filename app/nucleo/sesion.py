from fastapi import Request, Response  # type: ignore
from .configuracion import settings

# Helpers de sesión (cookie HTTPOnly) centralizados.

def obtener_token_cookie(request: Request) -> str | None:
    return request.cookies.get(settings.ACCESS_COOKIE_NAME)


def establecer_cookie_sesion(response: Response, token: str, max_age: int) -> None:
    """
    Establece la cookie de sesión con configuración de seguridad apropiada.
    
    La cookie es HTTPOnly para prevenir acceso desde JavaScript.
    El flag 'secure' se activa solo en producción (HTTPS).
    En desarrollo local (HTTP), secure=False permite que funcione sin SSL.
    """
    # Cookies seguras solo en producción (HTTPS)
    # En desarrollo local (HTTP) secure=True bloquearía la cookie
    es_produccion = settings.ENVIRONMENT == "production"
    
    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,  # Previene acceso desde JavaScript (XSS protection)
        secure=es_produccion,  # Solo HTTPS en producción
        samesite="lax",  # Protección CSRF moderada
        path="/",
    )


def eliminar_cookie_sesion(response: Response) -> None:
    """Elimina la cookie de sesión del cliente."""
    es_produccion = settings.ENVIRONMENT == "production"
    
    response.delete_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        path="/",
        secure=es_produccion,
        samesite="lax"
    )
