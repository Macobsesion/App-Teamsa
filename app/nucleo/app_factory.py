# Fábrica de aplicación FastAPI para centralizar configuración y registro de routers
#
# Responsabilidades principales:
# - Crear la instancia FastAPI y su ciclo de vida (lifespan) para tareas de arranque y apagado.
# - Preparar CORS y archivos estáticos (sirve /static desde la carpeta web).
# - Registrar routers de páginas (Jinja) y de API (módulos CRUD).
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import (
    http_exception_handler as default_http_exception_handler,
)
from starlette.requests import Request

from fastapi.exceptions import RequestValidationError  # type: ignore
import logging

from app.modulos.usuarios.usuarios_router import router as rt_usuarios, router_extra as rt_usuarios_extra
from app.modulos.clientes.clientes_router import router as rt_clientes
from app.modulos.servicios.servicios_router import router as rt_servicios
from app.modulos.proveedores.proveedores_router import router as rt_proveedores
from app.modulos.cotizaciones.cotizaciones_router import router as rt_cotizaciones
from app.modulos.ordenes.ordenes_router import router as rt_ordenes
from app.modulos.servicios_proveedores.servicios_proveedores_router import router as rt_servicios_proveedores
from app.modulos.ordenes_compra.ordenes_compra_router import router as rt_ordenes_compra
from app.modulos.ordenes_compra.wizard_router import router as rt_wizard_ordenes

from app.nucleo.base_datos import crear_tablas
from app.rutas import rt_autenticacion, rt_paginas
from app.nucleo.configuracion import settings
from starlette.middleware.base import BaseHTTPMiddleware
from app.web.jinja import get_templates

# Eventos
from app.base.eventos import BusEventos
from app.modulos.ordenes.eventos import (
    EVENTO_ORDEN_CREADA, handler_actualizar_cotizacion_aceptada,
    EVENTO_ORDEN_FINALIZADA, handler_cotizacion_finalizada,
    EVENTO_ORDEN_CANCELADA, handler_cotizacion_revertir_a_enviada
)

# Excepciones
from app.base.excepciones import AppError, RecursoNoEncontradoError, ReglaNegocioError, PermisoDenegadoError

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = ROOT_DIR / "web" / "static"
TEMPLATES_DIR = ROOT_DIR / "web" / "templates"


def create_app() -> FastAPI:
    # Registrar handlers de eventos al instanciar la app (idempotente gracias a BusEventos)
    BusEventos.suscribir(EVENTO_ORDEN_CREADA, handler_actualizar_cotizacion_aceptada)
    BusEventos.suscribir(EVENTO_ORDEN_FINALIZADA, handler_cotizacion_finalizada)
    BusEventos.suscribir(EVENTO_ORDEN_CANCELADA, handler_cotizacion_revertir_a_enviada)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger = logging.getLogger("teamsa")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            h = logging.StreamHandler()
            fmt = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")
            h.setFormatter(fmt)
            logger.addHandler(h)
        logger.info("La aplicación está iniciando…")
        try:
            crear_tablas()
            logger.info("La base de datos está lista.")
        except Exception as exc:
            logger.warning("Aviso al preparar la base de datos: %s", exc)
        yield
        logger.info("La aplicación se está apagando…")

    app = FastAPI(lifespan=lifespan)

    # CORS configurable desde variables de entorno
    allow_origins = (
        ["*"]
        if (settings.CORS_ALLOW_ORIGINS or "*").strip() == "*"
        else [o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",") if o.strip()]
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
    from app.nucleo.archivos import get_upload_root
    app.mount("/uploads", StaticFiles(directory=str(get_upload_root())), name="uploads")

    # # Handler global: para rutas de páginas (no /api/), devolver HTML en errores
    templates = get_templates()
    
    def _es_solicitud_de_pagina_html(ruta_solicitada: str) -> bool:
        """
        Determina si la solicitud es para una página HTML y no para la API.
        
        Args:
            ruta_solicitada: Path de la URL solicitada (ej: "/usuarios" o "/api/clientes")
            
        Returns:
            True si es una página HTML (no comienza con /api/), False si es API
        """
        return not ruta_solicitada.startswith("/api/")
    
    def _renderizar_pagina_de_error(
        request: Request,
        codigo_estado_http: int,
        mensaje_error: str
    ) -> templates.TemplateResponse:
        """
        Renderiza una página HTML de error usando la plantilla error.html.
        Al ser una página protegida por base.html (navbar), intentamos inyectar al usuario.
        """
        # Intentamos obtener la identidad del usuario para que el navbar no explote
        usuario_contexto = None
        from app.nucleo.sesion import obtener_token_cookie
        from app.nucleo.cls_identidad import obtener_gestor_identidad
        from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
        
        token = obtener_token_cookie(request)
        if token:
            try:
                u, r = obtener_gestor_identidad().extraer_identidad(token)
                usuario_contexto = UsuarioIdentity(usuario=u, rol=r)
            except Exception:
                pass

        contexto_template = {
            "request": request, # Importante para url_for y otros helpers
            "status": codigo_estado_http,
            "detail": mensaje_error,
            "usuario": usuario_contexto
        }
        return templates.TemplateResponse(
            request,
            "error.html",
            contexto_template,
            status_code=codigo_estado_http
        )

    
    @app.exception_handler(HTTPException)
    async def manejador_excepciones_http(request: Request, exc: HTTPException):  # type: ignore[override]
        """
        Maneja excepciones HTTP (401, 404, etc.) devolviendo HTML para páginas o JSON para API.
        """
        ruta_solicitada = request.url.path or ""
        encabezado_accept = request.headers.get("accept", "")
        
        es_pagina_html = _es_solicitud_de_pagina_html(ruta_solicitada)
        cliente_acepta_html = "text/html" in encabezado_accept or encabezado_accept == "*/*"
        es_htmx = request.headers.get("hx-request") == "true"
        
        if es_pagina_html and cliente_acepta_html and not es_htmx:
            # Personalizar mensaje según el código de error
            mensaje_error = exc.detail or ("No autenticado" if exc.status_code == 401 else "Error")
            return _renderizar_pagina_de_error(request, exc.status_code, mensaje_error)
        
        # Para solicitudes de API, usar el handler por defecto de FastAPI (devuelve JSON)
        return await default_http_exception_handler(request, exc)

    # ---- Helpers de Respuesta de Error ----

    def _responder_error_dominio(
        request: Request, exc: AppError, status_code: int
    ):
        """Helper reutilizable para responder errores de dominio en HTML o JSON."""
        ruta = request.url.path or ""
        es_htmx = request.headers.get("hx-request") == "true"
        
        if _es_solicitud_de_pagina_html(ruta) and not es_htmx:
            return _renderizar_pagina_de_error(request, status_code, exc.mensaje)
        return JSONResponse({"detail": exc.mensaje, "code": exc.codigo}, status_code=status_code)

    # ---- Handlers de Excepciones de Dominio ----

    @app.exception_handler(RecursoNoEncontradoError)
    async def manejador_no_encontrado(request: Request, exc: RecursoNoEncontradoError):
        """Maneja errores de recurso no encontrado (404)."""
        return _responder_error_dominio(request, exc, 404)

    @app.exception_handler(ReglaNegocioError)
    async def manejador_regla_negocio(request: Request, exc: ReglaNegocioError):
        """Maneja errores de reglas de negocio (409 Conflict o 422). Usamos 409 por defecto."""
        return _responder_error_dominio(request, exc, 409)

    @app.exception_handler(PermisoDenegadoError)
    async def manejador_permiso_denegado(request: Request, exc: PermisoDenegadoError):
        """Maneja errores de permisos (403)."""
        return _responder_error_dominio(request, exc, 403)

    @app.exception_handler(RequestValidationError)
    async def manejador_errores_de_validacion(request: Request, exc: RequestValidationError):
        """
        Maneja errores de validación de datos (campos faltantes, tipos incorrectos, etc.).
        """
        ruta_solicitada = request.url.path or ""
        es_pagina_html = _es_solicitud_de_pagina_html(ruta_solicitada)
        es_htmx = request.headers.get("hx-request") == "true"
        
        if es_pagina_html and not es_htmx:
            return _renderizar_pagina_de_error(request, 422, "Solicitud inválida")
        
        # Para API, devolver JSON con detalles de los errores de validación
        respuesta_json = {
            "detail": "Solicitud inválida",
            "errors": exc.errors()
        }
        return JSONResponse(respuesta_json, status_code=422)

    @app.exception_handler(Exception)
    async def manejador_excepciones_generales(request: Request, exc: Exception):  # pragma: no cover
        """
        Fallback para excepciones no controladas. Registra el error y devuelve página genérica.
        """
        # Registrar error completo en logs para debugging
        logging.getLogger("teamsa").error("Excepción no controlada: %s", exc, exc_info=True)
        
        ruta_solicitada = request.url.path or ""
        es_pagina_html = _es_solicitud_de_pagina_html(ruta_solicitada)
        es_htmx = request.headers.get("hx-request") == "true"
        
        if es_pagina_html and not es_htmx:
            return _renderizar_pagina_de_error(request, 500, "Error interno")
        
        # Para API, devolver JSON genérico
        return JSONResponse({"detail": "Error interno"}, status_code=500)


    # 404 HTML también para estáticos y rutas fuera de FastAPI (KISS):
    # Si la respuesta final es 404 y no es /api, devolvemos error.html
    class HtmlNotFoundMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):  # type: ignore[override]
            response = await call_next(request)
            try:
                path = request.url.path or ""
                accepts = request.headers.get("accept", "")
                is_page = not path.startswith("/api/")
                wants_html = ("text/html" in accepts) or (accepts == "*/*")
                if response.status_code == 404 and is_page and wants_html:
                    tpls = get_templates()
                    ruta = path or "/"
                    return tpls.TemplateResponse(
                        request,
                        "error.html",
                        {"status": 404, "detail": f"La pagina {ruta} no existe"},
                        status_code=404,
                    )
            except Exception:
                return response
            return response

    app.add_middleware(HtmlNotFoundMiddleware)

    routers = [
        rt_usuarios_extra,  # Primero: rutas específicas antes que el router genérico con {id}
        rt_paginas.router,
        rt_autenticacion.router,
        rt_usuarios,
        rt_clientes,
        rt_servicios,
        rt_proveedores,
        rt_cotizaciones,
        rt_ordenes,
        rt_servicios_proveedores,
        rt_ordenes_compra,
        rt_wizard_ordenes,

    ]
    for router in routers:
        app.include_router(router)

    return app
