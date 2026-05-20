"""Fábrica para orquestar la creación de módulos CRUD (API + UI)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.base.descriptor_crud import DescriptorCRUD, ConfiguracionUI
from app.base.enrutador_crud import construir_enrutador_crud
from app.base.ui_crud import DescriptorUI, construir_enrutador_ui


def crear_modulo_crud(
    *,
    descriptor: DescriptorCRUD,
    obtener_sesion: Callable[..., Session],
    actor_dependency: Callable,
    crear_dependency: Callable,
    editar_dependency: Callable,
    eliminar_dependency: Optional[Callable] = None,
    ver_dependency: Optional[Callable] = None,
    tpl_filas: str,
    tpl_form: str,
    validar_form_creacion: Optional[Callable[[dict[str, Any]], Optional[str]]] = None,
    validar_form_actualizacion: Optional[Callable[[dict[str, Any], Any], Optional[str]]] = None,
    extra_context_provider: Optional[Callable[[Session], dict[str, Any]]] = None,
    file_fields: Optional[dict[str, dict[str, Any]]] = None,
    routers_adicionales: Optional[list[APIRouter]] = None,
    routers_prioritarios: Optional[list[APIRouter]] = None,
    include_select_endpoint: bool = False,
    select_fields: Optional[list[str]] = None,
    select_filter_activo: bool = True,
    prefix_override: Optional[str] = None,
    nombre_modulo: Optional[str] = None,
) -> APIRouter:
    """Crea un router completo con API JSON y UI HTMX con permisos granulares."""
    
    # Crear router API JSON
    # Usamos crear_dependency y editar_dependency para las rutas correspondientes
    router_api = construir_enrutador_crud(
        prefix=descriptor.base_url,
        tag=descriptor.label,
        repo_factory=descriptor.repo_factory,
        schema_read=descriptor.schema_read,
        schema_create=descriptor.schema_create,
        schema_update=descriptor.schema_update,
        hooks=descriptor.build_hooks(),
        obtener_sesion=obtener_sesion,
        list_dependencies=[Depends(ver_dependency)] if ver_dependency else [Depends(actor_dependency)],
        create_dependency=crear_dependency,
        update_dependency=editar_dependency,
        delete_dependency=eliminar_dependency or editar_dependency,
        descriptor=descriptor,
    )
    
    # Router prioritario (/select) - SIEMPRE accesible para usuarios logueados para operatividad
    router_prioritario = APIRouter(
        prefix=descriptor.base_url, 
        tags=[descriptor.label],
        dependencies=[Depends(actor_dependency)]
    )

    if include_select_endpoint:
        campos = select_fields or ["id", "nombre"]

        def _mapear_item(item) -> dict:
            if hasattr(item, "serializar_select"):
                return item.serializar_select()
            item_dict: dict = {}
            for campo in campos:
                valor = getattr(item, campo, None)
                if isinstance(valor, Decimal):
                    valor = float(valor)
                item_dict[campo] = valor if valor is not None else ""
            return item_dict

        def _coercer_filtro(repo, key: str, value: str):
            columna = getattr(repo.modelo, key, None)
            if columna is None: return value
            try:
                python_type = columna.type.python_type
                if python_type == int: return int(value)
                if python_type == bool: return value.lower() in ('true', '1', 'yes')
            except Exception: pass
            return value

        @router_prioritario.get("/select", response_model=list[dict])
        def obtener_para_select(
            request: Request,
            db: Session = Depends(obtener_sesion)
        ):
            repo = descriptor.repo_factory(db)
            filtros: dict = {}
            if hasattr(repo, 'campos_filtrables'):
                for key, value in request.query_params.items():
                    if key in repo.campos_filtrables:
                        filtros[key] = _coercer_filtro(repo, key, value)
            
            items = repo.listar(filtros=filtros) if filtros else repo.listar()
            return [
                _mapear_item(i) for i in items 
                if not (select_filter_activo and hasattr(i, "activo") and not i.activo)
            ]
    
    ui_prefix = prefix_override or descriptor.base_url.replace("/api/", "/ui/")
    
    # Router UI HTMX
    router_ui = construir_enrutador_ui(
        prefix=ui_prefix,
        repo_factory=descriptor.repo_factory,
        schema_create=descriptor.schema_create,
        schema_update=descriptor.schema_update,
        hooks=descriptor.build_hooks(),
        obtener_sesion=obtener_sesion,
        list_dependencies=[Depends(ver_dependency)] if ver_dependency else [Depends(actor_dependency)],
        create_dependency=crear_dependency,
        update_dependency=editar_dependency,
        delete_dependency=eliminar_dependency,
        ui=DescriptorUI(
            tpl_filas=tpl_filas, 
            tpl_form=tpl_form,
            selectores=(descriptor.config_ui.selectores if descriptor.config_ui else {})
        ),
        label=descriptor.label,
        validar_form_creacion=validar_form_creacion,
        validar_form_actualizacion=validar_form_actualizacion,
        actor_dependency=actor_dependency,
        extra_context_provider=extra_context_provider,
        file_fields=file_fields,
        columnas=descriptor.frontend_config().get("columnas"),
        campo_busqueda=descriptor.campo_busqueda,
        nombre_modulo=nombre_modulo,
    )

    from fastapi.responses import HTMLResponse
    from app.web.jinja import get_templates
    
    ui_config = descriptor.config_ui or ConfiguracionUI()
    @router_ui.get("/", response_class=HTMLResponse)
    def vista_principal(
        request: Request, 
        db: Session = Depends(obtener_sesion),
        actor: Any = Depends(ver_dependency) if ver_dependency else Depends(actor_dependency)
    ):
        templates = get_templates()
        # Usar nombre_modulo como tópico para estabilidad en el refresco HTMX
        topic = ui_config.topic or nombre_modulo or descriptor.base_url.strip('/').replace('/', '_')
        
        from app.base.ui_crud import _obtener_usuario_db
        u_db = _obtener_usuario_db(db, actor)

        return templates.TemplateResponse("crud_page.html", {
            "request": request, 
            "crud_config": descriptor.frontend_config(),
            "ui_base": ui_prefix,
            "topic": topic,
            "usuario_actual": u_db
        })
    
    router_combinado = APIRouter()
    # ORDEN CRÍTICO: Prioritarios -> Select -> API -> UI -> Adicionales
    if routers_prioritarios:
        for r_p in routers_prioritarios: router_combinado.include_router(r_p)
    if include_select_endpoint:
        router_combinado.include_router(router_prioritario)
    router_combinado.include_router(router_api)
    router_combinado.include_router(router_ui)
    if routers_adicionales:
        for r_extra in routers_adicionales: router_combinado.include_router(r_extra)
    
    # Exportar routers internos para introspección si es necesario
    setattr(router_combinado, "router_api", router_api)
    setattr(router_combinado, "router_ui", router_ui)
    return router_combinado


def crear_modulo_crud_estandar(
    *,
    descriptor: DescriptorCRUD,
    nombre_modulo: str,
    include_select_endpoint: bool = False,
    select_fields: Optional[list[str]] = None,
    routers_prioritarios: Optional[list[APIRouter]] = None,
    routers_adicionales: Optional[list[APIRouter]] = None,
    validar_form_creacion: Optional[Callable[[dict[str, Any]], Optional[str]]] = None,
    validar_form_actualizacion: Optional[Callable[[dict[str, Any], Any], Optional[str]]] = None,
    extra_context_provider: Optional[Callable[[Session], dict[str, Any]]] = None,
    file_fields: Optional[dict[str, dict[str, Any]]] = None,
    prefix_override: Optional[str] = None,
) -> APIRouter:
    """Wrapper estandarizado que configura permisos granulares automáticamente."""
    from app.nucleo.base_datos import obtener_sesion_bd
    from app.rutas.dependencias import dp_usuario_actual
    from app.rutas.permisos import para_modulo
    
    return crear_modulo_crud(
        descriptor=descriptor,
        obtener_sesion=obtener_sesion_bd,
        actor_dependency=dp_usuario_actual,
        ver_dependency=para_modulo(nombre_modulo, "ver"),
        crear_dependency=para_modulo(nombre_modulo, "crear"),
        editar_dependency=para_modulo(nombre_modulo, "editar"),
        eliminar_dependency=para_modulo(nombre_modulo, "eliminar"),
        tpl_filas=f"ui/{nombre_modulo}/_filas.html",
        tpl_form=f"ui/{nombre_modulo}/_form.html",
        nombre_modulo=nombre_modulo,
        include_select_endpoint=include_select_endpoint,
        select_fields=select_fields,
        routers_prioritarios=routers_prioritarios,
        routers_adicionales=routers_adicionales,
        validar_form_creacion=validar_form_creacion,
        validar_form_actualizacion=validar_form_actualizacion,
        extra_context_provider=extra_context_provider,
        file_fields=file_fields,
        prefix_override=prefix_override
    )

__all__ = ["crear_modulo_crud", "crear_modulo_crud_estandar"]
