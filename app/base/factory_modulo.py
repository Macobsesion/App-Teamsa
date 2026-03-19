"""
Factory pattern para crear módulos CRUD completos con API + UI.

Este módulo elimina la duplicación de código en los routers de módulos
al centralizar la creación de routers API y UI con configuración estandarizada.
"""
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
    write_dependency: Callable,
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
) -> APIRouter:
    """
    Crea un router completo con API JSON y UI HTMX para un módulo CRUD.
    
    Esta función factory encapsula el patrón común de creación de routers
    que se repetía en todos los módulos, reduciendo duplicación y errores.
    
    Args:
        descriptor: DescriptorCRUD con configuración del módulo
        obtener_sesion: Dependencia para obtener sesión de DB
        actor_dependency: Dependencia para obtener usuario actual
        write_dependency: Dependencia para operaciones de escritura (ej: para_modulo)
        tpl_filas: Ruta al template de filas (ej: "ui/clientes/_filas.html")
        tpl_form: Ruta al template de formulario (ej: "ui/clientes/_form.html")
        validar_form_creacion: Validación opcional para formulario de creación
        validar_form_actualizacion: Validación opcional para formulario de actualización
        extra_context_provider: Función para agregar contexto extra a templates
        file_fields: Configuración de campos de archivos
        routers_adicionales: Lista de routers adicionales para incluir (ej: PDF, endpoints custom)
        include_select_endpoint: Si True, genera automáticamente endpoint /select para dropdowns
        select_fields: Campos a retornar en endpoint /select (default: ["id", "nombre"])
        select_filter_activo: Si True, solo retorna items con activo=True en /select
        
    Returns:
        APIRouter combinado con API JSON, UI HTMX y routers adicionales
        
    Ejemplo:
        ```python
        from app.base.factory_modulo import crear_modulo_crud
        from app.rutas.dependencias import dp_obtener_sesion_db, dp_usuario_actual
        from app.rutas.permisos import para_modulo
        
        # Módulo simple sin extras
        router = crear_modulo_crud(
            descriptor=descriptor_proveedores,
            obtener_sesion=dp_obtener_sesion_db,
            actor_dependency=dp_usuario_actual,
            write_dependency=para_modulo("proveedores", "editar"),
            tpl_filas="ui/proveedores/_filas.html",
            tpl_form="ui/proveedores/_form.html",
        )
        
        # Módulo con endpoint /select automático
        router = crear_modulo_crud(
            descriptor=descriptor_clientes,
            obtener_sesion=dp_obtener_sesion_db,
            actor_dependency=dp_usuario_actual,
            write_dependency=para_modulo("clientes", "editar"),
            tpl_filas="ui/clientes/_filas.html",
            tpl_form="ui/clientes/_form.html",
            include_select_endpoint=True,
            select_fields=["id", "nombre", "rfc", "email"],
        )
        
        # Módulo con routers adicionales
        router = crear_modulo_crud(
            descriptor=descriptor_viaticos,
            obtener_sesion=dp_obtener_sesion_db,
            actor_dependency=dp_usuario_actual,
            write_dependency=para_modulo("viaticos", "editar"),
            tpl_filas="ui/viaticos/_filas.html",
            tpl_form="ui/viaticos/_form.html",
            routers_adicionales=[gastos_router.router, pdf_router.router],
        )
        ```
    """
    # Crear router API JSON (GET/POST/PATCH/DELETE + /metadata)
    router_api = descriptor.to_api_router(
        obtener_sesion=obtener_sesion,
        list_dependencies=[Depends(actor_dependency)],
        write_dependency=write_dependency,
    )
    
    
    # Router para endpoints prioritarios (como /select) que deben evaluarse antes de las rutas genéricas
    # para evitar colisiones con /{id}
    router_prioritario = APIRouter(
        prefix=descriptor.base_url, 
        tags=[descriptor.label],
        dependencies=[Depends(actor_dependency)]
    )

    # Endpoint /select automático (si se solicita)
    if include_select_endpoint:
        campos = select_fields or ["id", "nombre"]

        def _mapear_item(item) -> dict:
            """Mapea un item del modelo a un dict con los campos solicitados."""
            # KISS: Permitir al modelo dictaminar cómo se serializa para selectores
            if hasattr(item, "serializar_select"):
                return item.serializar_select()

            item_dict: dict = {}
            for campo in campos:
                valor = getattr(item, campo, None)

                # Convertir Decimal a float para JSON
                if isinstance(valor, Decimal):
                    valor = float(valor)

                item_dict[campo] = valor if valor is not None else ""
            return item_dict

        def _coercer_filtro(repo, key: str, value: str):
            """Convierte el valor de query param al tipo correcto del modelo."""
            columna = getattr(repo.modelo, key, None)
            if columna is None:
                return value
            try:
                python_type = columna.type.python_type
                if python_type == int:
                    return int(value)
                if python_type == bool:
                    return value.lower() in ('true', '1', 'yes')
            except (AttributeError, ValueError):
                pass
            return value

        @router_prioritario.get("/select", response_model=list[dict])
        def obtener_para_select(
            request: Request,
            db: Session = Depends(obtener_sesion),
        ):
            """Endpoint automático para poblar selects/dropdowns."""
            repo = descriptor.repo_factory(db)

            filtros: dict = {}
            if hasattr(repo, 'campos_filtrables'):
                for key, value in request.query_params.items():
                    if key in repo.campos_filtrables:
                        filtros[key] = _coercer_filtro(repo, key, value)

            items = repo.listar(filtros=filtros) if filtros else repo.listar()

            return [
                _mapear_item(item)
                for item in items
                if not (select_filter_activo and hasattr(item, "activo") and not item.activo)
            ]
    
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

    # Añadir la vista principal al router UI
    # Esto se hace aquí para que pueda usar el `ui_prefix` y `actor_dependency`
    # del contexto de `crear_modulo_crud` y no tener que pasarlos a `construir_enrutador_ui`
    # solo para este endpoint.
    from fastapi.responses import HTMLResponse
    from app.web.jinja import get_templates
    
    ui_config = descriptor.config_ui or ConfiguracionUI()
    @router_ui.get("/", response_class=HTMLResponse)
    def vista_principal(request: Request, _actor: Any = Depends(actor_dependency)):
        """Devuelve la vista principal (listado) de la entidad generada desde base_crud.html."""
        templates = get_templates()
        return templates.TemplateResponse(
            "ui/base_crud.html",
            {
                "request": request,
                "configuracion": descriptor.frontend_config(),
                "topic": ui_config.topic or descriptor.base_url.strip('/').replace('/', '_')
            }
        )
    
    # Combinar routers: PRIORITARIOS -> API -> UI -> ADICIONALES
    router_combinado = APIRouter()
    if routers_prioritarios:
        for router_p in routers_prioritarios:
            router_combinado.include_router(router_p)
    if include_select_endpoint:
        router_combinado.include_router(router_prioritario)
    router_combinado.include_router(router_api)
    router_combinado.include_router(router_ui)
    
    # Incluir routers adicionales si se proporcionan
    if routers_adicionales:
        for router_extra in routers_adicionales:
            router_combinado.include_router(router_extra)
    
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
) -> APIRouter:
    """ Wrapper estandarizado para crear un módulo CRUD.
    
    Evita la duplicación en todos los routers al asumir valores por defecto para:
    - dependencias (sesion, usuario_actual, permisos para el módulo)
    - templates (ui/{nombre_modulo}/_filas.html, _form.html)
    """
    from app.nucleo.base_datos import obtener_sesion_bd
    from app.rutas.dependencias import dp_usuario_actual
    from app.rutas.permisos import para_modulo
    
    return crear_modulo_crud(
        descriptor=descriptor,
        obtener_sesion=obtener_sesion_bd,
        actor_dependency=dp_usuario_actual,
        write_dependency=para_modulo(nombre_modulo),
        tpl_filas=f"ui/{nombre_modulo}/_filas.html",
        tpl_form=f"ui/{nombre_modulo}/_form.html",
        include_select_endpoint=include_select_endpoint,
        select_fields=select_fields,
        routers_prioritarios=routers_prioritarios,
        routers_adicionales=routers_adicionales,
        validar_form_creacion=validar_form_creacion,
        validar_form_actualizacion=validar_form_actualizacion,
        extra_context_provider=extra_context_provider,
        file_fields=file_fields
    )

__all__ = ["crear_modulo_crud", "crear_modulo_crud_estandar"]
