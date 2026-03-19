"""
Enrutador UI genérico para CRUD con HTMX.

Objetivo: eliminar duplicación de endpoints HTML (filas/form/crear/actualizar/
eliminar) en los módulos. Se apoya en DescriptorCRUD y sus hooks para conservar
reglas de negocio (extra kwargs, validación de unicidad, etc.).

Se limita a:
- Renderizar filas y formulario (parciales Jinja)
- Procesar POST de crear/actualizar desde `request.form()`
- Disparar eventos HTMX para refrescar tabla y cerrar modal

No introduce nuevas dependencias y mantiene el comportamiento existente.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import traceback
from typing import Any, Callable, Optional, TypeVar

from fastapi import APIRouter, Depends, Request, Response, status, UploadFile  # type: ignore
from starlette.datastructures import UploadFile as StarletteUploadFile  # type: ignore
from fastapi.responses import HTMLResponse  # type: ignore
from pydantic import BaseModel, ValidationError  # type: ignore
from sqlmodel import Session  # type: ignore

from app.base.enrutador_crud import GanchosCRUD
from app.base.utiles_esquema import (
    obtener_campos_creables,
)
from app.web.jinja import get_templates
from app.nucleo.archivos import (
    save_pdf_temp,
    move_pdf_to_entity,
    save_pdf_for_entity,
)
from app.base.archivos_procesador import GestorArchivosPolimorfico
from app.base.procesador_formularios import ProcesadorFormulariosHTMX

# Tipos genéricos
RepoT = TypeVar("RepoT")
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)
ActorT = TypeVar("ActorT")


# La función `_es_nullable_o_numerico` fue eliminada aplicando principios KISS.
# La coerción de strings vacíos a None debe manejarse vía Pydantic (utiles_pydantic.py)
# o mediante un pre-procesamiento unificado sencillo.


@dataclass
class DescriptorUI:
    """Describe los parciales de UI y textos de feedback."""

    tpl_filas: str
    tpl_form: str
    msg_creado: str | None = None
    msg_actualizado: str | None = None
    msg_eliminado: str | None = None





def construir_enrutador_ui(
    *,
    prefix: str,
    repo_factory: Callable[[Session], RepoT],
    schema_create: type[CreateSchemaT],
    schema_update: type[UpdateSchemaT],
    hooks: GanchosCRUD[RepoT, CreateSchemaT, UpdateSchemaT, ActorT],
    obtener_sesion: Callable[..., Session],
    list_dependencies: Optional[list[Depends]] = None,
    write_dependency: Optional[Callable[..., ActorT]] = None,
    ui: DescriptorUI,
    label: str,
    validar_form_creacion: Optional[Callable[[dict[str, Any]], Optional[str]]] = None,
    validar_form_actualizacion: Optional[Callable[[dict[str, Any], Any], Optional[str]]] = None,
    actor_dependency: Optional[Callable[..., ActorT]] = None,
    extra_context_provider: Optional[Callable[[Session], dict[str, Any]]] = None,
    file_fields: Optional[dict[str, dict[str, Any]]] = None,
    columnas: Optional[list[dict[str, Any]]] = None,
    campo_busqueda: Optional[str] = None,
) -> APIRouter:
    """
    Genera un router con endpoints HTML para HTMX:
      - GET {prefix}/filas
      - GET {prefix}/form
      - POST {prefix}/crear
      - POST {prefix}/{id}/actualizar
      - DELETE {prefix}/{id}

    Detalles:
    - Usa los mismos hooks que la API (crear/actualizar/unicidad)
    - Emite eventos HTMX para refrescar tabla, cerrar modal y mostrar flash
    - Si `actor_dependency` se provee, inyecta el actor y calcula `puede_editar`
      (rol == "admin") para que los parciales puedan ocultar acciones
    """

    router = APIRouter(prefix=prefix, tags=["UI"], include_in_schema=False, dependencies=list_dependencies or [])
    templates = get_templates()

    # Mensajes por defecto derivados del label (simple singularización quitando 's')
    singular = label[:-1] if label.lower().endswith("s") else label
    msg_creado = ui.msg_creado or f"{singular} creado"
    msg_actualizado = ui.msg_actualizado or f"{singular} actualizado"
    msg_eliminado = ui.msg_eliminado or f"{singular} eliminado"

    def _get_repo(db: Session) -> RepoT:
        return repo_factory(db)

    @router.get("/filas", response_class=HTMLResponse)
    def ui_filas(
        request: Request,
        db: Session = Depends(obtener_sesion),
        actor: ActorT | None = Depends(actor_dependency) if actor_dependency else None,
    ):
        repo = _get_repo(db)
        filtros: dict[str, Any] = {}
        try:
            q = request.query_params.get('q')
            if campo_busqueda and q:
                filtros[campo_busqueda] = q
            if hasattr(repo, 'campos_filtrables'):
                for k, v in request.query_params.items():
                    if k in getattr(repo, 'campos_filtrables') and v is not None and v != '':
                        filtros[k] = v
        except Exception:
            filtros = {}
        # type: ignore[attr-defined]
        items = repo.listar(filtros)
        # Interrogamos el usuario real de DB para verificar ocultamiento de botones HTMX
        puede_editar = False
        puede_eliminar = False
        if actor:
            from app.modulos.usuarios.usuarios_modelo import Usuario
            from sqlmodel import select
            usuario_db = db.exec(select(Usuario).where(Usuario.usuario == getattr(actor, "usuario", ""))).first()
            if usuario_db:
                # Inferencia de módulo desde URL
                modulo = prefix.strip("/").split("/")[-1].replace("-", "_")
                # Respetamos los checkboxes como fuente de verdad para ocultar botones
                puede_editar = modulo in (getattr(usuario_db, "permisos_editar", []) or [])
                puede_eliminar = modulo in (getattr(usuario_db, "permisos_eliminar", []) or [])
                    
        return templates.TemplateResponse(request, ui.tpl_filas, {
            "items": items,
            "puede_editar": puede_editar,
            "puede_eliminar": puede_eliminar,
            "ui_base": prefix,
            "columnas": columnas or [],
        })

    @router.get("/form", response_class=HTMLResponse)
    def ui_form(
        request: Request,
        id: int | None = None,
        modo: str = "crear",
        db: Session = Depends(obtener_sesion),
        actor: ActorT | None = Depends(actor_dependency) if actor_dependency else None,
    ):
        repo = _get_repo(db)
        # type: ignore[attr-defined]
        item = repo.db.get(repo.modelo, id) if id else None
        # Determinar si puede editar basándose en rol o permisos por módulo
        puede_editar = False
        if actor:
            from app.modulos.usuarios.usuarios_modelo import Usuario
            from sqlmodel import select
            usuario_db = db.exec(select(Usuario).where(Usuario.usuario == getattr(actor, "usuario", ""))).first()
            if usuario_db:
                if usuario_db.rol == "admin":
                    puede_editar = True
                else:
                    modulo = prefix.strip("/").split("/")[-1].replace("-", "_")
                    puede_editar = modulo in (getattr(usuario_db, "permisos_editar", []) or [])

        extra_ctx = extra_context_provider(db) if extra_context_provider else {}
        ctx = {"request": request, "item": item, "modo": modo, "puede_editar": puede_editar}
        ctx.update(extra_ctx)
        return templates.TemplateResponse(request, ui.tpl_form, ctx)

    @router.post("/crear")
    async def ui_crear(
        request: Request,
        response: Response,
        actor: ActorT = Depends(write_dependency) if write_dependency else None,
        db: Session = Depends(obtener_sesion),
    ):
        repo = _get_repo(db)
        form = await request.form()

        # Validación UI opcional
        if validar_form_creacion:
            error = validar_form_creacion(dict(form))
            if error:
                return templates.TemplateResponse(
                    request, ui.tpl_form,
                    {"item": None, "modo": "crear", "error": error},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        creables = set(obtener_campos_creables(schema_create))
        props = schema_create.model_json_schema().get("properties", {})
        datos_filtrados, archivos_temp = ProcesadorFormulariosHTMX.procesar(
            form, props, creables, file_fields
        )

        try:
            payload = schema_create(**datos_filtrados)
        except ValidationError as e:  # pragma: no cover
            return templates.TemplateResponse(
                request, ui.tpl_form,
                {"item": None, "modo": "crear", "error": str(e)},
                status_code=200,
            )

        if hooks.validar_unicidad:
            conflicto = hooks.validar_unicidad(repo, payload)  # type: ignore[arg-type]
            if conflicto:
                return templates.TemplateResponse(
                    request, ui.tpl_form,
                    {"item": None, "modo": "crear", "error": conflicto},
                    status_code=200,
                )

        base = hooks.preparar_creacion(payload, actor)  # type: ignore[arg-type]
        extras = hooks.extra_kwargs_creacion(payload, actor)  # type: ignore[arg-type]
        combinado: dict[str, Any] = {**base, **(extras or {})}
        try:
            entidad = repo.crear(**combinado)
        except Exception as exc:
            traceback.print_exc()
            return templates.TemplateResponse(
                request, ui.tpl_form,
                {"item": None, "modo": "crear", "error": f"Error interno: {str(exc)}"},
                status_code=200,
            )

        # POLIMORFISMO: Confirmar guardado de archivos moviéndolos a destino final
        if archivos_temp:
            plural = label.strip().lower()
            entidad_id = getattr(entidad, "id", None)
            if entidad_id is not None:
                cambios: dict[str, Any] = {}
                for campo, temps in archivos_temp.items():
                    cfg = (file_fields or {}).get(campo, {})
                    estrategia = GestorArchivosPolimorfico.obtener_estrategia(bool(cfg.get("multiple")))
                    try:
                        finales = estrategia.confirmar_guardado(temps, int(entidad_id), plural, cfg)
                        if finales is not None:
                            cambios[campo] = finales
                    except ValueError as e:
                        return templates.TemplateResponse(
                            request, ui.tpl_form,
                            {"item": entidad, "modo": "editar", "error": str(e)},
                            status_code=200,
                        )
                if cambios:
                    repo.actualizar(int(entidad_id), cambios)

        response.headers["HX-Trigger"] = json.dumps({
            "refrescarLista": True, "modalClose": True,
            "flash": {"tipo": "success", "texto": msg_creado},
        })
        response.headers["HX-Refresh"] = "true"
        return HTMLResponse("")

    @router.post("/{id}/actualizar")
    async def ui_actualizar(
        id: int,
        request: Request,
        response: Response,
        actor: ActorT = Depends(write_dependency) if write_dependency else None,
        db: Session = Depends(obtener_sesion),
    ):
        repo = _get_repo(db)
        entidad_actual = repo.db.get(repo.modelo, id)
        form = await request.form()

        props_u = schema_update.model_json_schema().get("properties", {})
        campos_u = set(props_u.keys())
        datos_u, archivos_update = ProcesadorFormulariosHTMX.procesar(
            form, props_u, campos_u, file_fields,
            entity_id=id, entity_plural=label.strip().lower()
        )

        # POLIMORFISMO: Fusionar actualizaciones de archivos
        for campo, nuevos in list(archivos_update.items()):
            cfg = (file_fields or {}).get(campo, {})
            is_multiple = bool(cfg.get("multiple"))
            estrategia = GestorArchivosPolimorfico.obtener_estrategia(is_multiple)
            
            try:
                entidad = repo.db.get(repo.modelo, id)
                actuales = list(getattr(entidad, campo, []) or []) if entidad else []
            except Exception:
                actuales = []
                
            try:
                fusionados = estrategia.fusionar_actualizacion(nuevos, actuales, cfg)
                archivos_update[campo] = fusionados
            except ValueError as e:
                return templates.TemplateResponse(
                    request, ui.tpl_form,
                    {"item": entidad_actual, "modo": "editar", "error": str(e)},
                    status_code=200,
                )

        # Validación de formulario de actualización
        if validar_form_actualizacion is not None:
            msg = validar_form_actualizacion(datos_u, entidad_actual)
            if msg:
                return templates.TemplateResponse(
                    request, ui.tpl_form,
                    {"item": entidad_actual, "modo": "editar", "error": msg},
                    status_code=200,
                )

        try:
            payload = schema_update(**datos_u)
        except ValidationError as e:  # pragma: no cover
            return templates.TemplateResponse(
                request, ui.tpl_form,
                {"item": None, "modo": "editar", "error": str(e)},
                status_code=200,
            )
        base = hooks.preparar_actualizacion(payload, actor)  # type: ignore[arg-type]
        extras = hooks.extra_kwargs_actualizacion(payload, actor)  # type: ignore[arg-type]
        combinado: dict[str, Any] = {**base, **(extras or {}), **archivos_update}
        try:
            repo.actualizar(id, combinado)
        except Exception as exc:
            traceback.print_exc()
            return templates.TemplateResponse(
                request, ui.tpl_form,
                {"item": entidad_actual, "modo": "editar", "error": f"Error interno: {str(exc)}"},
                status_code=200,
            )

        response.headers["HX-Trigger"] = json.dumps({
            "refrescarLista": True, "modalClose": True,
            "flash": {"tipo": "success", "texto": msg_actualizado},
        })
        response.headers["HX-Refresh"] = "true"
        return HTMLResponse("")

    from sqlalchemy.exc import IntegrityError

    @router.delete("/{id}")
    def ui_eliminar(
        id: int,
        response: Response,
        actor: ActorT = Depends(write_dependency) if write_dependency else None,
        db: Session = Depends(obtener_sesion),
    ):
        repo = _get_repo(db)
        try:
            repo.eliminar(id)
            response.headers["HX-Trigger"] = json.dumps({
                "refrescarLista": True,
                "flash": {"tipo": "success", "texto": msg_eliminado},
            })
        except IntegrityError:
            db.rollback()
            response.headers["HX-Trigger"] = json.dumps({
                "flash": {"tipo": "error", "texto": "No se puede eliminar este registro porque está siendo utilizado en otros documentos (ej: cotizaciones u órdenes)."},
            })
        except Exception as e:
            db.rollback()
            response.headers["HX-Trigger"] = json.dumps({
                "flash": {"tipo": "error", "texto": f"Error al eliminar: {str(e)}"},
            })
            
        return HTMLResponse("")

    return router


__all__ = ["DescriptorUI", "construir_enrutador_ui"]
