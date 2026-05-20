from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select, desc
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.permisos import para_modulo
from app.base.logs_modelo import LogActividad
from app.web.jinja import get_templates

router = APIRouter(prefix="/ui/admin/logs", tags=["Admin - Logs"])
TEMPLATES = get_templates()

@router.get("/")
def listar_logs(
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    usuario = Depends(para_modulo("usuarios", "ver"))
):
    """Muestra la pantalla de logs de actividad (audit log)."""
    # Verificación extra de ROL para mayor seguridad
    if getattr(usuario, "rol", "") != "admin":
        from app.base.excepciones import PermisoDenegadoError
        raise PermisoDenegadoError("Acceso exclusivo para administradores")

    # Obtener los últimos 100 logs
    statement = select(LogActividad).order_by(desc(LogActividad.fecha)).limit(100)
    logs = db.exec(statement).all()

    return TEMPLATES.TemplateResponse(
        "ui/logs/lista.html",
        {
            "request": request,
            "logs": logs,
            "usuario": usuario
        }
    )
