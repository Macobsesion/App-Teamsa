"""
Factory pattern para crear módulos CRUD completos con API + UI.

Este módulo elimina la duplicación de código en los routers de módulos
al centralizar la creación de routers API y UI con configuración estandarizada.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.base.descriptor_crud import DescriptorCRUD
from app.base.ui_crud import DescriptorUI, construir_enrutador_ui


def crear_modulo_crud(
    *,
    descriptor: DescriptorCRUD,
    obtener_sesion: Callable[..., Session],
    actor_dependency: Callable,
    write_dependency: Callable,
    tpl_filas: str,
    tpl_form: str,
    validar_form_creacion: Optional[Callable[[dict[str, Any]], Optional[str]]] = None,
    validar_form_actualizacion: Optional[Callable[[dict[str, Any], Any], Optional[str]]] = None,
    extra_context_provider: Optional[Callable[[Session], dict[str, Any]]] = None,
    file_fields: Optional[dict[str, dict[str, Any]]] = None,
) -> APIRouter:
    """
    Crea un router completo con API JSON y UI HTMX para un módulo CRUD.
    
    Esta función factory encapsula el patrón común de creación de routers
    que se repetía en todos los módulos, reduciendo duplicación y errores.
    
    Args:
        descriptor: DescriptorCRUD con configuración del módulo
        obtener_sesion: Dependencia para obtener sesión de DB
        actor_dependency: Dependencia para obtener usuario actual
        write_dependency: Dependencia para operaciones de escritura (ej: exigir_roles)
        tpl_filas: Ruta al template de filas (ej: "ui/clientes/_filas.html")
        tpl_form: Ruta al template de formulario (ej: "ui/clientes/_form.html")
        validar_form_creacion: Validación opcional para formulario de creación
        validar_form_actualizacion: Validación opcional para formulario de actualización
        extra_context_provider: Función para agregar contexto extra a templates
        file_fields: Configuración de campos de archivos
        endpoints_adicionales: Lista de (method, path, handler) para endpoints custom
        
    Returns:
        APIRouter combinado con API JSON y UI HTMX
        
    Ejemplo:
        ```python
        from app.base.factory_modulo import crear_modulo_crud
        from app.rutas.dependencias import dp_obtener_sesion_db, dp_usuario_actual, exigir_roles
        
        router = crear_modulo_crud(
            descriptor=descriptor_clientes,
            obtener_sesion=dp_obtener_sesion_db,
            actor_dependency=dp_usuario_actual,
            write_dependency=exigir_roles("admin"),
            tpl_filas="ui/clientes/_filas.html",
            tpl_form="ui/clientes/_form.html",
        )
        ```
    """
    # Crear router API JSON (GET/POST/PATCH/DELETE + /metadata)
    router_api = descriptor.to_api_router(
        obtener_sesion=obtener_sesion,
        list_dependencies=[Depends(actor_dependency)],
        write_dependency=write_dependency,
    )
    
    # Derivar prefix de UI desde el base_url de API
    ui_prefix = descriptor.base_url.replace("/api/", "/ui/")
    
    # Crear router UI HTMX (GET /filas, GET /form, POST /crear, etc.)
    router_ui = construir_enrutador_ui(
        prefix=ui_prefix,
        repo_factory=descriptor.repo_factory,
        schema_create=descriptor.schema_create,
        schema_update=descriptor.schema_update,
        hooks=descriptor.build_hooks(),
        obtener_sesion=obtener_sesion,
        list_dependencies=[Depends(actor_dependency)],
        write_dependency=write_dependency,
        ui=DescriptorUI(
            tpl_filas=tpl_filas,
            tpl_form=tpl_form,
        ),
        label=descriptor.label,
        validar_form_creacion=validar_form_creacion,
        validar_form_actualizacion=validar_form_actualizacion,
        actor_dependency=actor_dependency,
        extra_context_provider=extra_context_provider,
        file_fields=file_fields,
        columnas=descriptor.frontend_config().get("columnas"),
        campo_busqueda=descriptor.campo_busqueda,
    )
    
    # Combinar routers API + UI
    router_combinado = APIRouter()
    router_combinado.include_router(router_api)
    router_combinado.include_router(router_ui)
    
    return router_combinado


__all__ = ["crear_modulo_crud"]
