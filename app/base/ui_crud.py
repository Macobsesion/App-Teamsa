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

# Tipos genéricos
RepoT = TypeVar("RepoT")
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)
ActorT = TypeVar("ActorT")


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
        puede_editar = bool(actor and getattr(actor, "rol", None) == "admin")
        return templates.TemplateResponse(ui.tpl_filas, {
            "request": request,
            "items": items,
            "puede_editar": puede_editar,
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
        puede_editar = bool(actor and getattr(actor, "rol", None) == "admin")
        extra_ctx = extra_context_provider(db) if extra_context_provider else {}
        ctx = {"request": request, "item": item, "modo": modo, "puede_editar": puede_editar}
        ctx.update(extra_ctx)
        return templates.TemplateResponse(ui.tpl_form, ctx)

    @router.post("/crear")
    async def ui_crear(
        request: Request,
        response: Response,
        actor: ActorT = Depends(write_dependency) if write_dependency else None,
        db: Session = Depends(obtener_sesion),
    ):
        repo = _get_repo(db)
        form = await request.form()

        # Validación UI opcional (p.ej. confirmación de contraseña)
        if validar_form_creacion:
            error = validar_form_creacion(dict(form))
            if error:
                return templates.TemplateResponse(
                    ui.tpl_form,
                    {"request": request, "item": None, "modo": "crear", "error": error},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        # Filtra según el esquema de creación
        creables = set(obtener_campos_creables(schema_create))
        # Detectar campos de tipo lista para recoger múltiples valores del FormData
        props = schema_create.model_json_schema().get("properties", {})
        def _es_array_prop(defn: dict[str, Any]) -> bool:
            if defn.get("type") == "array":
                return True
            # Pydantic puede emitir anyOf con array|null
            for key in ("anyOf", "oneOf", "allOf"):
                lst = defn.get(key) or []
                if isinstance(lst, list) and any(isinstance(d, dict) and d.get("type") == "array" for d in lst):
                    return True
            # Si hay "items" es indicio de array
            return "items" in defn
        array_fields = {k for k, v in props.items() if isinstance(v, dict) and _es_array_prop(v)}
        datos_filtrados: dict[str, Any] = {}
        archivos_temp: dict[str, str] = {}
        for k in creables:
            if k not in form:
                continue
            # Primero tratar campos tipo array (incluye input multiple de archivos)
            is_array = (k in array_fields) or bool((file_fields or {}).get(k, {}).get("multiple"))
            if is_array and hasattr(form, "getlist"):
                lista = form.getlist(k)
                if lista and isinstance(lista[0], (UploadFile, StarletteUploadFile)):
                    rutas: list[str] = []
                    for f in lista:
                        if not (f and (f.filename or "").strip()):
                            continue
                        try:
                            rutas.append(save_pdf_temp(f))
                        except Exception as e:  # pragma: no cover
                            return templates.TemplateResponse(
                                ui.tpl_form,
                                {"request": request, "item": None, "modo": "crear", "error": f"Archivo inválido: {e}"},
                                status_code=200,
                            )
                    if rutas:
                        archivos_temp[k] = rutas
                    datos_filtrados[k] = rutas
                else:
                    # valores de texto simples en arrays
                    datos_filtrados[k] = lista
                continue

            # Caso campo simple (no array)
            val = form.get(k)
            if isinstance(val, (UploadFile, StarletteUploadFile)) and (val.filename or "").strip():
                try:
                    temp_rel = save_pdf_temp(val)
                except Exception as e:  # pragma: no cover
                    return templates.TemplateResponse(
                        ui.tpl_form,
                        {"request": request, "item": None, "modo": "crear", "error": f"Archivo inválido: {e}"},
                        status_code=200,
                    )
                archivos_temp.setdefault(k, [])
                archivos_temp[k].append(temp_rel)
                datos_filtrados[k] = temp_rel
            else:
                datos_filtrados[k] = val
        # Coerción KISS: vacíos a None para campos numéricos opcionales
        def _is_numeric(defn: dict[str, Any]) -> bool:
            t = defn.get("type")
            if t in ("integer", "number"):
                return True
            for key in ("anyOf", "oneOf", "allOf"):
                lst = defn.get(key) or []
                if isinstance(lst, list) and any(isinstance(d, dict) and d.get("type") in ("integer", "number") for d in lst):
                    return True
            return False
        for k, v in list(datos_filtrados.items()):
            defn = props.get(k, {}) if isinstance(props, dict) else {}
            if _is_numeric(defn) and isinstance(v, str) and v.strip() == "":
                datos_filtrados[k] = None

        try:
            payload = schema_create(**datos_filtrados)
        except ValidationError as e:  # pragma: no cover
            return templates.TemplateResponse(
                ui.tpl_form,
                {"request": request, "item": None, "modo": "crear", "error": str(e)},
                status_code=200,
            )
        # Validación de unicidad (si existe)
        if hooks.validar_unicidad:
            conflicto = hooks.validar_unicidad(repo, payload)  # type: ignore[arg-type]
            if conflicto:
                return templates.TemplateResponse(
                    ui.tpl_form,
                    {"request": request, "item": None, "modo": "crear", "error": conflicto},
                    status_code=200,
                )

        base = hooks.preparar_creacion(payload, actor)  # type: ignore[arg-type]
        extras = hooks.extra_kwargs_creacion(payload, actor)  # type: ignore[arg-type]
        combinado: dict[str, Any] = {**base, **(extras or {})}
        # type: ignore[attr-defined]
        entidad = repo.crear(**combinado)

        if archivos_temp:
            cambios: dict[str, Any] = {}
            plural = label.strip().lower()
            entidad_id = getattr(entidad, "id", None)
            if entidad_id is not None:
                for campo, temps in archivos_temp.items():
                    cfg = (file_fields or {}).get(campo)
                    if isinstance(temps, list):
                        finales: list[str] = []
                        for t in temps:
                            final_rel = move_pdf_to_entity(t, entity_plural=plural, entity_id=int(entidad_id))
                            finales.append(final_rel)
                        # Validar máximo de archivos si se indicó
                        if cfg and cfg.get("multiple") and cfg.get("max"):
                            if len(finales) > int(cfg["max"]):
                                return templates.TemplateResponse(
                                    ui.tpl_form,
                                    {"request": request, "item": entidad, "modo": "editar", "error": f"Máximo {int(cfg['max'])} archivos"},
                                    status_code=200,
                                )
                        # Si el campo es múltiple, asignamos lista; si no, el primero
                        cambios[campo] = finales if (cfg and cfg.get("multiple")) else (finales[0] if finales else None)
                    else:
                        final_rel = move_pdf_to_entity(temps, entity_plural=plural, entity_id=int(entidad_id))
                        cambios[campo] = final_rel
                if cambios:
                    repo.actualizar(int(entidad_id), cambios)

        # Señales HTMX
        response.headers["HX-Trigger"] = json.dumps({
            "refrescarLista": True,
            "modalClose": True,
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
        # entidad actual para validaciones contextuales
        entidad_actual = repo.db.get(repo.modelo, id)
        form = await request.form()
        # Recoger datos teniendo en cuenta arrays según schema_update
        props_u = schema_update.model_json_schema().get("properties", {})
        array_fields_u = {k for k, v in props_u.items() if v.get("type") == "array"}
        datos_u: dict[str, Any] = {}
        archivos_update: dict[str, str] = {}
        # Para actualización, si llegan archivos nuevos:
        for k in props_u.keys():
            if k not in form:
                continue
            # Primero tratar arrays (posibles múltiples archivos)
            is_array_u = (k in array_fields_u) or bool((file_fields or {}).get(k, {}).get("multiple"))
            if is_array_u and hasattr(form, "getlist"):
                lista = form.getlist(k)
                if lista and isinstance(lista[0], (UploadFile, StarletteUploadFile)):
                    finales: list[str] = []
                    for f in lista:
                        if not (f and (f.filename or "").strip()):
                            continue
                        final_rel = save_pdf_for_entity(f, entity_plural=label.strip().lower(), entity_id=int(id))
                        finales.append(final_rel)
                    current = []
                    try:
                        entidad = repo.db.get(repo.modelo, id)
                        current = list(getattr(entidad, k, []) or []) if entidad else []
                    except Exception:
                        current = []
                    combinado_lista = current + finales
                    max_files = (file_fields or {}).get(k, {}).get("max")
                    if max_files and len(combinado_lista) > int(max_files):
                        return templates.TemplateResponse(
                            ui.tpl_form,
                            {"request": request, "item": entidad, "modo": "editar", "error": f"Máximo {int(max_files)} archivos"},
                            status_code=200,
                        )
                    archivos_update[k] = combinado_lista
                else:
                    datos_u[k] = lista
                continue

            # Caso campo simple (no array)
            val = form.get(k)
            if isinstance(val, (UploadFile, StarletteUploadFile)) and (val.filename or "").strip():
                try:
                    final_rel = save_pdf_for_entity(val, entity_plural=label.strip().lower(), entity_id=int(id))
                except Exception as e:  # pragma: no cover
                    return templates.TemplateResponse(
                        ui.tpl_form,
                        {"request": request, "item": None, "modo": "editar", "error": f"Archivo inválido: {e}"},
                        status_code=200,
                    )
                if file_fields and file_fields.get(k, {}).get("multiple"):
                    current = []
                    try:
                        entidad = repo.db.get(repo.modelo, id)
                        current = list(getattr(entidad, k, []) or []) if entidad else []
                    except Exception:
                        current = []
                    combinado_lista = current + [final_rel]
                    max_files = (file_fields or {}).get(k, {}).get("max")
                    if max_files and len(combinado_lista) > int(max_files):
                        return templates.TemplateResponse(
                            ui.tpl_form,
                            {"request": request, "item": entidad, "modo": "editar", "error": f"Máximo {int(max_files)} archivos"},
                            status_code=200,
                        )
                    archivos_update[k] = combinado_lista
                else:
                    archivos_update[k] = final_rel
            else:
                datos_u[k] = val
        # Coerción KISS: vacíos a None para campos numéricos opcionales en update
        props_u = schema_update.model_json_schema().get("properties", {})
        def _is_numeric_u(defn: dict[str, Any]) -> bool:
            t = defn.get("type")
            if t in ("integer", "number"):
                return True
            for key in ("anyOf", "oneOf", "allOf"):
                lst = defn.get(key) or []
                if isinstance(lst, list) and any(isinstance(d, dict) and d.get("type") in ("integer", "number") for d in lst):
                    return True
            return False
        for k, v in list(datos_u.items()):
            defn = props_u.get(k, {}) if isinstance(props_u, dict) else {}
            if _is_numeric_u(defn) and isinstance(v, str) and v.strip() == "":
                datos_u[k] = None

        # Validación de formulario de actualización (suave, UI)
        if validar_form_actualizacion is not None:
            msg = validar_form_actualizacion(datos_u, entidad_actual)
            if msg:
                return templates.TemplateResponse(
                    ui.tpl_form,
                    {"request": request, "item": entidad_actual, "modo": "editar", "error": msg},
                    status_code=200,
                )

        try:
            payload = schema_update(**datos_u)
        except ValidationError as e:  # pragma: no cover
            return templates.TemplateResponse(
                ui.tpl_form,
                {"request": request, "item": None, "modo": "editar", "error": str(e)},
                status_code=200,
            )
        base = hooks.preparar_actualizacion(payload, actor)  # type: ignore[arg-type]
        extras = hooks.extra_kwargs_actualizacion(payload, actor)  # type: ignore[arg-type]
        combinado: dict[str, Any] = {**base, **(extras or {}), **archivos_update}
        # type: ignore[attr-defined]
        repo.actualizar(id, combinado)

        response.headers["HX-Trigger"] = json.dumps({
            "refrescarLista": True,
            "modalClose": True,
            "flash": {"tipo": "success", "texto": msg_actualizado},
        })
        response.headers["HX-Refresh"] = "true"
        return HTMLResponse("")

    @router.delete("/{id}")
    def ui_eliminar(
        id: int,
        response: Response,
        actor: ActorT = Depends(write_dependency) if write_dependency else None,
        db: Session = Depends(obtener_sesion),
    ):
        repo = _get_repo(db)
        # type: ignore[attr-defined]
        repo.eliminar(id)
        response.headers["HX-Trigger"] = json.dumps({
            "refrescarLista": True,
            "flash": {"tipo": "success", "texto": msg_eliminado},
        })
        response.headers["HX-Refresh"] = "true"
        return HTMLResponse("")

    return router

__all__ = ["DescriptorUI", "construir_enrutador_ui"]
