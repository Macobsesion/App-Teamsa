from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from typing import Any

from app.rutas.dependencias import dp_obtener_sesion_db, dp_usuario_actual
from app.rutas.permisos import para_modulo
from app.modulos.auditoria.auditoria_repositorio import RepositorioAuditoria
from app.web.jinja import get_templates

router = APIRouter(prefix="/auditoria", tags=["Auditoría"])

@router.get("/", response_class=HTMLResponse)
def listar_logs_pagina(
    request: Request,
    modulo: str | None = Query(None),
    usuario_filtro: str | None = Query(None, alias="usuario"),
    accion: str | None = Query(None),
    q: str | None = Query(None),
    db: Session = Depends(dp_obtener_sesion_db),
    actor: Any = Depends(para_modulo("auditoria", "ver"))
):
    """Vista principal del panel de auditoría."""
    repo = RepositorioAuditoria(db)
    templates = get_templates()
    
    filtros = {}
    if modulo: filtros["modulo"] = modulo
    if usuario_filtro: filtros["usuario"] = usuario_filtro
    if accion: filtros["accion"] = accion
    if q: filtros["q"] = q
    
    logs = repo.listar_logs(filtros, limite=50)
    
    contexto = {
        "request": request,
        "logs": logs,
        "filtros": filtros,
        "usuario": actor
    }
    
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "ui/auditoria/_tabla_logs.html", contexto)
        
    return templates.TemplateResponse(request, "ui/auditoria/lista.html", contexto)
