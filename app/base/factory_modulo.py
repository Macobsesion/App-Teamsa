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
        write_dependency: Dependencia para operaciones de escritura (ej: exigir_roles)
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
        from app.rutas.dependencias import dp_obtener_sesion_db, dp_usuario_actual, exigir_roles
        
        # Módulo simple sin extras
        router = crear_modulo_crud(
            descriptor=descriptor_proveedores,
            obtener_sesion=dp_obtener_sesion_db,
            actor_dependency=dp_usuario_actual,
            write_dependency=exigir_roles("admin"),
            tpl_filas="ui/proveedores/_filas.html",
            tpl_form="ui/proveedores/_form.html",
        )
        
        # Módulo con endpoint /select automático
        router = crear_modulo_crud(
            descriptor=descriptor_clientes,
            obtener_sesion=dp_obtener_sesion_db,
            actor_dependency=dp_usuario_actual,
            write_dependency=exigir_roles("admin"),
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
            write_dependency=exigir_roles("admin"),
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
        
        @router_prioritario.get("/select", response_model=list[dict])
        def obtener_para_select(
            request: Request,  # Request de FastAPI/Starlette
            db: Session = Depends(obtener_sesion),
            # El usuario ya viene validado por la dependencia del router
        ):
            """Endpoint automático para poblar selects/dropdowns."""
            
            repo = descriptor.repo_factory(db)
            
            # Construir filtros desde query params
            filtros = {}
            if hasattr(request, 'query_params'):
                for key, value in request.query_params.items():
                    # Solo aplicar filtros si el campo es filtrable en el repositorio
                    if hasattr(repo, 'campos_filtrables') and key in repo.campos_filtrables:
                        # Convertir el valor al tipo correcto según la columna del modelo
                        columna = getattr(descriptor.repo_factory.modelo, key, None)
                        if columna is not None:
                            # Obtener el tipo Python de la columna
                            try:
                                python_type = columna.type.python_type
                                # Convertir el string del query param al tipo correcto
                                if python_type == int:
                                    filtros[key] = int(value)
                                elif python_type == bool:
                                    filtros[key] = value.lower() in ('true', '1', 'yes')
                                else:
                                    filtros[key] = value
                            except (AttributeError, ValueError):
                                # Si no se puede determinar el tipo, usar el valor como string
                                filtros[key] = value
                        else:
                            filtros[key] = value
            
            # Listar con filtros si los hay
            if filtros:
                items = repo.listar(filtros=filtros)
            else:
                items = repo.listar()
            
            resultado = []
            for item in items:
                # Filtrar por activo si se solicita y el campo existe
                if select_filter_activo and hasattr(item, "activo") and not item.activo:
                    continue
                
                # Construir dict con campos solicitados
                item_dict = {}
                for campo in campos:
                    # Soportar navegación por relaciones (ej: "proveedor.nombre")
                    if "." in campo:
                        partes = campo.split(".", 1)
                        objeto_relacionado = getattr(item, partes[0], None)
                        valor = getattr(objeto_relacionado, partes[1], None) if objeto_relacionado else None
                    else:
                        valor = getattr(item, campo, None)
                    
                    # Convertir Decimal a float para JSON
                    if isinstance(valor, Decimal):
                        valor = float(valor)
                    
                    # Convertir None a string vacío para mejor UX en selects
                    item_dict[campo] = valor if valor is not None else ""
                
                resultado.append(item_dict)
            
            return resultado
    
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


__all__ = ["crear_modulo_crud"]
