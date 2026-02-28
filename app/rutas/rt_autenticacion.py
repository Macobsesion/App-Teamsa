# Rutas de autenticación (cookie-only con JWT).
#
# Este endpoint recibe credenciales desde un formulario (content-type: x-www-form-urlencoded),
# valida contra la base de datos y emite un JWT que se guarda en una cookie HTTPOnly
# para ser utilizada por el resto de rutas protegidas.
from typing import Any
import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Response, status  # type: ignore
from sqlmodel import Session  # type: ignore

from app.modulos.usuarios.usuarios_repositorio import RepositorioUsuario
from app.nucleo.cls_autenticacion import GestorAutenticacion, obtener_gestor_autenticacion
from app.nucleo.configuracion import settings
from app.nucleo.sesion import establecer_cookie_sesion, eliminar_cookie_sesion
from app.rutas.dependencias import dp_obtener_sesion_db

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _obtener_repo(db: Session) -> RepositorioUsuario:
    return RepositorioUsuario(db)


def _obtener_gestor_autenticacion() -> GestorAutenticacion:
    return obtener_gestor_autenticacion()


@router.post("/validaUsuario")
def login(
    response: Response,
    txtNombre: str = Form(...),
    txtPassword: str = Form(...),
    db: Session = Depends(dp_obtener_sesion_db),
    gestor_autenticacion: GestorAutenticacion = Depends(_obtener_gestor_autenticacion),
):
    repo = _obtener_repo(db)
    usuario = repo.obtener_por_campo("usuario", txtNombre)
    logger = logging.getLogger("teamsa")
    # Verifica la contraseña contra el hash almacenado en DB
    if not usuario or not gestor_autenticacion.verificar_contrasena(txtPassword, usuario.contrasena):
        logger.warning("Login fallido para usuario '%s'", txtNombre)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    token = gestor_autenticacion.crear_token_acceso(
        datos={"sub": usuario.usuario, "rol": usuario.rol}
    )
    max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    establecer_cookie_sesion(response, token, max_age)
    logger.info("Login exitoso de '%s' (rol=%s)", usuario.usuario, usuario.rol)
    return {"token_type": "cookie", "expires_in": max_age, "rol": usuario.rol}  # type: ignore[return-value]


@router.get("/salir", include_in_schema=False)
def salir():
    """Limpia la cookie de sesión y redirige al inicio (/)."""
    from fastapi.responses import RedirectResponse #type: ignore

    resp = RedirectResponse(url="/", status_code=302)
    eliminar_cookie_sesion(resp)
    return resp
