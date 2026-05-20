"""
Fábrica de la aplicación FastAPI.
Configura middlewares, rutas, base de datos y eventos de ciclo de vida.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import (
    http_exception_handler as default_http_exception_handler,
)
from starlette.middleware.base import BaseHTTPMiddleware

from app.nucleo.configuracion import settings
from app.nucleo.base_datos import inicializar_bd
from app.base.constantes import STATIC_DIR, UPLOADS_DIR, get_upload_root
from app.web.jinja import get_templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de inicio y cierre de la aplicación."""
    # Inicio: asegurar que la base de datos y tablas existen
    inicializar_bd()
    
    # Registrar suscriptores a eventos de negocio
    from app.nucleo.eventos_inicializar import registrar_eventos_globales
    registrar_eventos_globales()
    
    yield
    # Cierre: limpieza si es necesaria


def create_app() -> FastAPI:
    """Crea y configura la instancia principal de FastAPI."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
    )

    # Configuración de CORS
    allow_origins = (
        [o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",") if o.strip()]
        if settings.CORS_ALLOW_ORIGINS and settings.CORS_ALLOW_ORIGINS != "*"
        else ["*"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Servir activos estáticos (CSS/JS/Imagenes) usados por las vistas Jinja
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    
    # Directorio de subidas (PDFs): se monta si existe, o se creará al primer upload
    uploads_path = get_upload_root()
    uploads_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

    # Middleware de Contexto de Identidad (Audit Sentinel)
    from app.nucleo.contexto import establecer_usuario_actual
    from app.nucleo.sesion import obtener_token_cookie
    from app.nucleo.cls_identidad import obtener_gestor_identidad
    
    @app.middleware("http")
    async def identity_context_middleware(request: Request, call_next):
        path = request.url.path
        
        # BYPASS PARA RUTAS ESTÁTICAS Y PÚBLICAS (No requieren identidad)
        # Evita 401 o carga innecesaria en activos y login
        if path.startswith("/static") or path.startswith("/uploads") or path.startswith("/auth") or path == "/salud":
            return await call_next(request)

        # Log de entrada para depuración
        logging.getLogger("teamsa").info(f"Petición entrante: {request.method} {path}")

        token = obtener_token_cookie(request)
        usuario = None
        if token:
            try:
                u, _ = obtener_gestor_identidad().extraer_identidad(token)
                usuario = u
            except Exception:
                pass
        
        # Establecer identidad en el contexto del hilo/tarea actual
        establecer_usuario_actual(usuario)
        
        response = await call_next(request)
        return response

    # Handler global para errores 404 en páginas HTML
    templates = get_templates()

    def _renderizar_pagina_de_error(request: Request, codigo_estado_http: int, mensaje_error: str):
        """Renderiza una página HTML de error inyectando el usuario para que la navbar funcione."""
        usuario_contexto = None
        from app.nucleo.sesion import obtener_token_cookie
        from app.nucleo.cls_identidad import obtener_gestor_identidad
        
        token = obtener_token_cookie(request)
        if token:
            try:
                u, _ = obtener_gestor_identidad().extraer_identidad(token)
                from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
                usuario_contexto = UsuarioIdentity(usuario=u, rol=_)
            except Exception:
                pass

        return templates.TemplateResponse(
            "error.html",
            {"request": request, "status": codigo_estado_http, "detail": mensaje_error, "usuario": usuario_contexto},
            status_code=codigo_estado_http
        )

    def _es_peticion_html_no_htmx(request: Request) -> bool:
        """Determina si la solicitud es para una página HTML completa (no API ni HTMX)."""
        path = request.url.path
        accept = request.headers.get("accept", "")
        es_htmx = request.headers.get("hx-request") == "true"
        return not path.startswith("/api/") and ("text/html" in accept or accept == "*/*") and not es_htmx

    @app.exception_handler(404)
    async def custom_404_handler(request: Request, exc):
        if _es_peticion_html_no_htmx(request):
            return _renderizar_pagina_de_error(request, 404, "Página no encontrada")
        return await default_http_exception_handler(request, exc)

    from fastapi import HTTPException
    from fastapi.responses import RedirectResponse
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Maneja excepciones HTTP, redirigiendo al login en caso de 401."""
        if exc.status_code == 401:
            if _es_peticion_html_no_htmx(request):
                return RedirectResponse(url="/?error=sesion_expirada", status_code=302)
        
        if _es_peticion_html_no_htmx(request):
            mensaje = exc.detail or "Error"
            return _renderizar_pagina_de_error(request, exc.status_code, mensaje)
        
        return await default_http_exception_handler(request, exc)

    from app.base.excepciones import AppError, RecursoNoEncontradoError, ReglaNegocioError, PermisoDenegadoError

    @app.exception_handler(AppError)
    @app.exception_handler(ReglaNegocioError)
    @app.exception_handler(RecursoNoEncontradoError)
    @app.exception_handler(PermisoDenegadoError)
    async def app_exception_handler(request: Request, exc: AppError):
        """Maneja errores de dominio y negocio, devolviendo códigos HTTP semánticos."""
        status_code = 400
        if isinstance(exc, RecursoNoEncontradoError):
            status_code = 404
        elif isinstance(exc, PermisoDenegadoError):
            status_code = 403
        
        # Loggear solo el mensaje para errores de negocio (no el traceback completo)
        logging.getLogger("teamsa").warning(f"Error de Negocio [{exc.codigo}]: {exc.mensaje}")
        
        if _es_peticion_html_no_htmx(request):
            return _renderizar_pagina_de_error(request, status_code, exc.mensaje)
        
        return JSONResponse(
            status_code=status_code,
            content={
                "detail": exc.mensaje,
                "mensaje": exc.mensaje,
                "codigo": exc.codigo
            }
        )

    @app.exception_handler(RequestValidationError)
    async def manejador_errores_de_validacion(request: Request, exc: RequestValidationError):
        """Maneja errores de validación de datos (campos faltantes, tipos incorrectos)."""
        if _es_peticion_html_no_htmx(request):
            return _renderizar_pagina_de_error(request, 422, "Solicitud inválida")
        
        return JSONResponse(
            {"detail": "Solicitud inválida", "errors": exc.errors()},
            status_code=422
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Capturar cualquier excepción no controlada (Error 500)
        # Si por alguna razón AppError llega aquí, lo manejamos correctamente
        if isinstance(exc, AppError):
            return await app_exception_handler(request, exc)
            
        logging.getLogger("teamsa").error(f"Error inesperado: {str(exc)}", exc_info=True)
        
        if _es_peticion_html_no_htmx(request):
            return _renderizar_pagina_de_error(request, 500, "Ha ocurrido un error inesperado")
        
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "tipo": type(exc).__name__}
        )

    # Middleware para capturar 404s que Starlette lanza antes del exception_handler
    class HtmlNotFoundMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            if response.status_code == 404:
                path = request.url.path
                wants_html = "text/html" in request.headers.get("accept", "")
                if not path.startswith("/api/") and wants_html:
                    return templates.TemplateResponse(
                        "error.html", 
                        {"request": request, "status": 404, "detail": "Recurso no encontrado"},
                        status_code=404
                    )
            return response

    app.add_middleware(HtmlNotFoundMiddleware)

    # Registro de Routers
    from app.rutas import rt_paginas, rt_autenticacion, rt_catalogos, rt_admin
    
    # Importar modelos para asegurar que el registro de SQLModel/SQLAlchemy sea completo
    # y se resuelvan las relaciones de texto (ej. "Cliente") correctamente.
    from app.modulos.clientes.clientes_modelo import Cliente
    from app.modulos.proveedores.proveedores_modelo import Proveedor
    from app.modulos.servicios.servicios_modelo import Servicio
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
    from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo, ConceptoOrdenTrabajo
    from app.modulos.viaticos.viaticos_modelo import Viatico, ViaticoOrdenEnlace
    from app.modulos.usuarios.usuarios_modelo import Usuario
    from app.modulos.servicios_proveedores.servicios_proveedores_modelo import ServicioProveedor
    from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra, DetalleOrdenCompra
    from app.base.logs_modelo import LogActividad

    # FORZAR resolución de mappers (Regla de Oro para evitar NameError en Relationships)
    from sqlalchemy.orm import configure_mappers
    configure_mappers()

    from app.modulos.cotizaciones.cotizaciones_router import router as rt_cotizaciones
    from app.modulos.ordenes_trabajo.ordenes_trabajo_router import router as rt_ordenes_trabajo
    from app.modulos.viaticos.viaticos_router import router as rt_viaticos
    from app.modulos.usuarios.usuarios_router import router as rt_usuarios
    from app.modulos.ordenes_compra.ordenes_compra_router import router as rt_ordenes_compra
    from app.modulos.cronograma.cronograma_router import router_cronograma_ui, router_cronograma_api
    from app.modulos.auditoria.auditoria_router import router as rt_auditoria
    
    # Rutas de API y Datos
    app.include_router(rt_autenticacion.router)
    app.include_router(rt_catalogos.router)
    app.include_router(rt_cotizaciones)
    app.include_router(rt_ordenes_trabajo)
    app.include_router(rt_viaticos)
    app.include_router(rt_usuarios)
    app.include_router(rt_ordenes_compra)
    app.include_router(rt_admin.router)
    app.include_router(router_cronograma_api)
    app.include_router(router_cronograma_ui)
    app.include_router(rt_auditoria)
    
    # Rutas de Páginas Web (HTML)
    app.include_router(rt_paginas.router)

    @app.get("/salud", tags=["Sistema"])
    async def salud():
        """Endpoint de salud para monitoreo."""
        return {"estado": "ok", "version": "1.0.0"}

    return app
