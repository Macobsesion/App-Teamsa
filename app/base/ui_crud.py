from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import traceback
from typing import Any, Callable, Optional, TypeVar

from sqlalchemy.exc import IntegrityError
from app.base.excepciones import ReglaNegocioError, PermisoDenegadoError

from fastapi import APIRouter, Depends, Request, Response, status, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ValidationError
from sqlmodel import Session, Field

from app.base.enrutador_crud import GanchosCRUD
from app.base.utiles_esquema import obtener_campos_creables
from app.web.jinja import get_templates
from app.base.archivos_procesador import GestorArchivosPolimorfico
from app.base.procesador_formularios import ProcesadorFormulariosHTMX

# Logger
logger = logging.getLogger("teamsa.ui_crud")

class DescriptorUI:
    def __init__(
        self, 
        tpl_filas: str, 
        tpl_form: str, 
        msg_creado: str | None = None, 
        msg_actualizado: str | None = None, 
        msg_eliminado: str | None = None,
        selectores: dict[str, Any] | None = None,
        prefix: str | None = None
    ):
        self.tpl_filas = tpl_filas
        self.tpl_form = tpl_form
        self.msg_creado = msg_creado
        self.msg_actualizado = msg_actualizado
        self.msg_eliminado = msg_eliminado
        self.selectores = selectores or {}
        self.prefix = prefix

    def __str__(self):
        return self.prefix or ""


def _obtener_usuario_db(db: Session, actor: Any):
    """Obtiene el objeto Usuario completo de la BD a partir del actor de identidad.
    Centraliza la consulta para evitar duplicación en las vistas."""
    if not actor:
        return None
    from app.modulos.usuarios.usuarios_modelo import Usuario
    from sqlmodel import select
    return db.exec(select(Usuario).where(Usuario.usuario == getattr(actor, "usuario", ""))).first()


def construir_enrutador_ui(
    *,
    prefix: str,
    repo_factory: Callable[[Session], Any],
    schema_create: type[BaseModel],
    schema_update: type[BaseModel],
    hooks: GanchosCRUD,
    obtener_sesion: Callable[..., Session],
    list_dependencies: Optional[list[Depends]] = None,
    create_dependency: Optional[Callable[..., Any]] = None,
    update_dependency: Optional[Callable[..., Any]] = None,
    delete_dependency: Optional[Callable[..., Any]] = None,
    ui: DescriptorUI,
    label: str,
    validar_form_creacion: Optional[Callable] = None,
    validar_form_actualizacion: Optional[Callable] = None,
    actor_dependency: Optional[Callable] = None,
    extra_context_provider: Optional[Callable] = None,
    file_fields: Optional[dict] = None,
    columnas: Optional[list] = None,
    campo_busqueda: Optional[str] = None,
    nombre_modulo: str | None = None,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=["UI"], include_in_schema=False, dependencies=list_dependencies or [])
    templates = get_templates()

    singular = label[:-1] if label.lower().endswith("s") else label
    msg_creado = ui.msg_creado or f"{singular} creado"
    msg_actualizado = ui.msg_actualizado or f"{singular} actualizado"
    ui.prefix = prefix
    msg_eliminado = ui.msg_eliminado or f"{singular} eliminado"

    def _get_repo(db: Session) -> Any:
        return repo_factory(db)

    def _formatear_error(e: Exception) -> str:
        """Traduce excepciones técnicas a mensajes amigables y específicos para la UI."""
        if isinstance(e, ValidationError):
            errores = []
            for err in e.errors():
                campo = str(err.get('loc', [-1])[-1]).replace('_', ' ').capitalize()
                msg = err.get('msg', 'valor inválido')
                errores.append(f"<b>{campo}</b>: {msg}")
            return "Error de validación:<br>" + "<br>".join(errores)
        
        if isinstance(e, IntegrityError):
            msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            if "duplicate key" in msg.lower():
                return "Error de duplicidad: Ya existe un registro con estos datos únicos."
            if "not-null constraint" in msg.lower():
                return "Error de integridad: Faltan campos obligatorios para completar la operación."
            return f"Error de base de datos: {msg}"
            
        if hasattr(e, 'mensaje'): # AppError
            return str(e.mensaje)
            
        return str(e)

    @router.get("/filas", response_class=HTMLResponse)
    def ui_filas(
        request: Request,
        db: Session = Depends(obtener_sesion),
        actor: Any = Depends(actor_dependency) if actor_dependency else None,
    ):
        # Consulta única del usuario completo para RBAC + seguridad + permisos de botones
        u_db = _obtener_usuario_db(db, actor)

        # RBAC: Verificar permiso de "ver"
        if nombre_modulo and u_db:
            if nombre_modulo not in (u_db.permisos_ver or []):
                raise PermisoDenegadoError(f"No tienes permiso para ver {label}")

        repo = _get_repo(db)
        filtros = {}
        pagina = 1
        LIMITE_PAGINA = 10
        try:
            pagina = int(request.query_params.get("pagina", 1))
            q = request.query_params.get('q')
            if q: filtros['q'] = q
            if hasattr(repo, 'campos_filtrables'):
                for k, v in request.query_params.items():
                    if k in repo.campos_filtrables and v:
                        filtros[k] = v
        except Exception: pass

        # Inyectar filtros de seguridad si el repositorio lo soporta
        filtros = repo.aplicar_seguridad_filtro(filtros, u_db)
            
        total_registros = repo.contar(filtros)
        from math import ceil
        total_paginas = max(1, ceil(total_registros / LIMITE_PAGINA))
        pagina = max(1, min(pagina, total_paginas))
        
        items = repo.listar(filtros, limite=LIMITE_PAGINA, desplazamiento=(pagina - 1) * LIMITE_PAGINA)
        
        # Permisos para botones
        puede_editar = False
        puede_eliminar = False
        es_admin = False
        if u_db:
            mod_key = nombre_modulo or prefix.strip("/").split("/")[-1].replace("-", "_")
            puede_editar = mod_key in (u_db.permisos_editar or [])
            puede_eliminar = mod_key in (u_db.permisos_eliminar or [])
            es_admin = getattr(u_db, "rol", "") == "admin"

        logger.debug(f"Paginación: {ui.prefix} | Pag: {pagina}/{total_paginas}")

        return templates.TemplateResponse(ui.tpl_filas, {
            "request": request,
            "items": items,
            "puede_editar": puede_editar,
            "puede_eliminar": puede_eliminar,
            "es_admin": es_admin,
            "usuario_actual": u_db,
            "ui_base": ui,
            "columnas": columnas or [],
            "pagina_actual": pagina,
            "total_paginas": total_paginas,
            "total_registros": total_registros,
        })

    @router.get("/form", response_class=HTMLResponse)
    def ui_form(
        request: Request,
        id: int | None = None,
        modo: str = "crear",
        db: Session = Depends(obtener_sesion),
        actor: Any = Depends(actor_dependency) if actor_dependency else None,
    ):
        # Consulta única del usuario completo
        u_db = _obtener_usuario_db(db, actor)

        if nombre_modulo and u_db:
            permiso_req = "editar" if id else "crear"
            lista = getattr(u_db, f"permisos_{permiso_req}", []) or []
            if nombre_modulo not in lista:
                raise PermisoDenegadoError(f"No tienes permiso para {permiso_req} en {label}")

        repo = _get_repo(db)
        item = repo.db.get(repo.modelo, id) if id else None
        puede_editar = False
        es_admin = False
        if u_db:
            mod_key = nombre_modulo or prefix.strip("/").split("/")[-1].replace("-", "_")
            puede_editar = mod_key in (u_db.permisos_editar or [])
            es_admin = getattr(u_db, "rol", "") == "admin"

        extra_ctx = extra_context_provider(db) if extra_context_provider else {}
        ctx = {
            "request": request, 
            "item": item, 
            "modo": modo, 
            "puede_editar": puede_editar, 
            "es_admin": es_admin, 
            "usuario_actual": u_db,
            "ui_base": ui
        }
        ctx.update(extra_ctx)
        return templates.TemplateResponse(ui.tpl_form, ctx)

    @router.post("/crear")
    async def ui_crear(
        request: Request,
        response: Response,
        actor: Any = Depends(actor_dependency) if actor_dependency else None,
        db: Session = Depends(obtener_sesion),
        _permiso: Any = Depends(create_dependency) if create_dependency else None,
    ):
        repo = _get_repo(db)
        form = await request.form()
        if validar_form_creacion:
            err = validar_form_creacion(dict(form))
            if err: 
                headers = {"HX-Trigger": json.dumps({"mostrarError": err})}
                return templates.TemplateResponse(ui.tpl_form, {"request": request, "item": None, "modo": "crear", "error": err}, status_code=200, headers=headers)

        creables = set(obtener_campos_creables(schema_create))
        props = schema_create.model_json_schema().get("properties", {})
        datos, archivos = ProcesadorFormulariosHTMX.procesar(form, props, creables, file_fields)

        try:
            payload = schema_create(**datos)
            if hooks.validar_unicidad:
                conflicto = hooks.validar_unicidad(repo, payload)
                if conflicto: 
                    headers = {"HX-Trigger": json.dumps({"mostrarError": conflicto})}
                    return templates.TemplateResponse(ui.tpl_form, {"request": request, "item": None, "modo": "crear", "error": conflicto}, status_code=200, headers=headers)

            base = hooks.preparar_creacion(payload, actor)
            extras = (hooks.extra_kwargs_creacion(payload, actor) or {}).copy()
            
            # Detección robusta del actor para auditoría
            u_login = getattr(actor, "usuario", None) or getattr(actor, "nombre", None) or "SISTEMA"
            logger.debug(f"AUDITORIA UI - Actor: {u_login}")
            
            # Blindaje forzoso
            if not extras.get("creado_por"): extras["creado_por"] = u_login
            if not extras.get("modificado_por"): extras["modificado_por"] = u_login
            
            datos_finales = {**base, **extras}
            logger.debug(f"AUDITORIA UI - Campos finales: {list(datos_finales.keys())}")
            
            entidad = repo.crear(datos_finales)
            
            if archivos and hasattr(entidad, "id"):
                cambios = {}
                for campo, temps in archivos.items():
                    estrategia = GestorArchivosPolimorfico.obtener_estrategia(bool((file_fields or {}).get(campo, {}).get("multiple")))
                    try:
                        finales = estrategia.confirmar_guardado(temps, int(entidad.id), label.strip().lower(), (file_fields or {}).get(campo, {}))
                        if finales: cambios[campo] = finales
                    except ValueError as e: return templates.TemplateResponse(ui.tpl_form, {"request": request, "item": entidad, "modo": "editar", "error": str(e)}, status_code=200)
                if cambios: repo.actualizar(entidad.id, cambios)

            # Registrar Log de Actividad
            from app.base.logs_servicio import ServicioLogs
            ServicioLogs.registrar(
                usuario=u_login, 
                accion="CREAR", 
                modulo=(nombre_modulo or label.lower()), 
                detalles=str(getattr(entidad, "id", ""))
            )

            response.headers["HX-Trigger"] = json.dumps({"refrescarLista": True, "modalClose": True, "flash": {"tipo": "success", "texto": msg_creado}})
            response.headers["HX-Refresh"] = "true"
            return HTMLResponse("")
        except Exception as e:
            msg_err = _formatear_error(e)
            headers = {"HX-Trigger": json.dumps({"mostrarError": msg_err})}
            return templates.TemplateResponse(ui.tpl_form, {"request": request, "item": None, "modo": "crear", "error": msg_err, "ui_base": ui}, status_code=200, headers=headers)

    @router.post("/{id}/actualizar")
    async def ui_actualizar(
        id: int,
        request: Request,
        response: Response,
        actor: Any = Depends(actor_dependency) if actor_dependency else None,
        db: Session = Depends(obtener_sesion),
        _permiso: Any = Depends(update_dependency) if update_dependency else None,
    ):
        repo = _get_repo(db)
        entidad_actual = repo.db.get(repo.modelo, id)
        form = await request.form()
        props = schema_update.model_json_schema().get("properties", {})
        datos, archivos = ProcesadorFormulariosHTMX.procesar(form, props, set(props.keys()), file_fields, entity_id=id, entity_plural=label.strip().lower())

        try:
            payload = schema_update(**datos)
            base = hooks.preparar_actualizacion(payload, actor)
            extras = (hooks.extra_kwargs_actualizacion(payload, actor) or {}).copy()
            
            # Asegurar auditoría
            u_login = getattr(actor, "usuario", None) or getattr(actor, "nombre", None) or "SISTEMA"
            if not extras.get("modificado_por"): extras["modificado_por"] = u_login
            logger.debug(f"AUDITORIA UI UPDATE - Actor: {u_login}")
            
            repo.actualizar(id, {**base, **archivos, **extras})
            
            # Registrar Log de Actividad
            from app.base.logs_servicio import ServicioLogs
            ServicioLogs.registrar(
                usuario=u_login, 
                accion="EDITAR", 
                modulo=(nombre_modulo or label.lower()), 
                detalles=str(id)
            )

            response.headers["HX-Trigger"] = json.dumps({"refrescarLista": True, "modalClose": True, "flash": {"tipo": "success", "texto": msg_actualizado}})
            response.headers["HX-Refresh"] = "true"
            return HTMLResponse("")
        except Exception as e:
            msg_err = _formatear_error(e)
            headers = {"HX-Trigger": json.dumps({"mostrarError": msg_err})}
            return templates.TemplateResponse(ui.tpl_form, {"request": request, "item": entidad_actual, "modo": "editar", "error": msg_err, "ui_base": ui}, status_code=200, headers=headers)

    # Dependencia de borrado
    dep_borrado = delete_dependency or (lambda: None)

    @router.delete("/{id}")
    def ui_eliminar(
        id: int,
        response: Response,
        db: Session = Depends(obtener_sesion),
        _actor: Any = Depends(dep_borrado),
    ):
        repo = _get_repo(db)
        try:
            repo.eliminar(id)
            
            # Registrar Log de Actividad
            u_login = getattr(_actor, "usuario", None) or getattr(_actor, "nombre", None) or "SISTEMA"
            from app.base.logs_servicio import ServicioLogs
            ServicioLogs.registrar(
                usuario=u_login, 
                accion="ELIMINAR", 
                modulo=(nombre_modulo or label.lower()), 
                detalles=str(id)
            )

            response.headers["HX-Trigger"] = json.dumps({
                "refrescarLista": True,
                "flash": {"tipo": "success", "texto": msg_eliminado},
            })
            response.headers["HX-Refresh"] = "true"
            return HTMLResponse("")

        except (IntegrityError, ReglaNegocioError, ValueError) as e:
            msg = str(e)
            if isinstance(e, IntegrityError):
                db.rollback()
                msg = "No se puede eliminar: el registro está en uso por otros documentos."
            
            logger.warning(f"UI DELETE BLOCKED: {label} {id}: {msg}")
            
            headers = {
                "HX-Reswap": "none",
                "HX-Trigger": json.dumps({"flash": {"tipo": "danger", "texto": msg}})
            }
            return HTMLResponse("", status_code=200, headers=headers)

        except Exception as e:
            logger.error(f"UI DELETE ERROR: {traceback.format_exc()}")
            headers = {
                "HX-Reswap": "none",
                "HX-Trigger": json.dumps({"flash": {"tipo": "danger", "texto": f"Error técnico: {str(e)}"}})
            }
            return HTMLResponse("", status_code=500, headers=headers)

    return router

__all__ = ["construir_enrutador_ui", "DescriptorUI"]
