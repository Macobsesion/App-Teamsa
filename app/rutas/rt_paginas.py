# Rutas HTML (render de plantillas protegidas).
#
# Este módulo orquesta páginas Jinja que usan HTMX en el frontend.
# - Cada vista entrega `crud_config` (metadatos/columnas) y un `ui_base`.
# - `ui_base` apunta a los endpoints HTML de cada módulo (prefijo `/ui/...`).
# - El HTML (crud_page.html) usa hx-get/hx-post para cargar filas y formularios
#   en el modal, evitando JS personalizado y manteniendo la UI declarativa.
from pathlib import Path

from fastapi import APIRouter, Depends, Request  # type: ignore
from fastapi.responses import HTMLResponse  # type: ignore
from app.web.jinja import get_templates

from app.modulos.usuarios.usuarios_router import descriptor as usuarios_descriptor
from app.modulos.clientes.clientes_router import descriptor as clientes_descriptor
from app.modulos.servicios.servicios_router import descriptor as servicios_descriptor
from app.modulos.proveedores.proveedores_router import descriptor as proveedores_descriptor
from app.modulos.cotizaciones.cotizaciones_router import descriptor as cotizaciones_descriptor
from app.modulos.ordenes_trabajo.ordenes_trabajo_router import descriptor as ordenes_descriptor
from app.modulos.servicios_proveedores.servicios_proveedores_router import descriptor as servicios_proveedores_descriptor
from app.modulos.ordenes_compra.ordenes_compra_router import descriptor as ordenes_compra_descriptor
from app.modulos.viaticos.viaticos_router import descriptor as viaticos_descriptor

from app.rutas.permisos import para_modulo

router = APIRouter()
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "web" / "templates"
templates = get_templates()

def render_crud_page(request: Request, *, template: str, descriptor, ui_base: str, usuario, modulo: str) -> HTMLResponse:
    """
    Renderiza una página CRUD genérica.
    - `descriptor.frontend_config()` aporta columnas (thead) y etiquetas.
    - `ui_base` es la base de rutas HTMX para filas (`/filas`) y formulario (`/form`).
    """
    # Lógica de permisos para la UI: Admin tiene todo, otros consultan sus arrays JSON
    perms_edit = getattr(usuario, "permisos_editar", []) or []
    perms_create = getattr(usuario, "permisos_crear", []) or []
    perms_delete = getattr(usuario, "permisos_eliminar", []) or []
    
    # Para la UI, consultamos sus arrays JSON de permisos
    puede_editar = modulo in perms_edit
    puede_crear = modulo in perms_create
    puede_eliminar = modulo in perms_delete
    
    # Calcular tópico para refrescos HTMX (consistente con factory_modulo)
    topic = (descriptor.config_ui.topic if descriptor.config_ui else None) or modulo
    
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "crud_config": descriptor.frontend_config(),
            "ui_base": ui_base,
            "topic": topic,
            "puede_editar": puede_editar,
            "puede_crear": puede_crear,
            "puede_eliminar": puede_eliminar,
            "usuario": usuario,
        },
    )

@router.get("/salud", include_in_schema=False)
def salud():
    return {"status": "ok"}

@router.get("/", response_class=HTMLResponse)
def mostrar_login(request: Request):
    # Página de autenticación (no protegida)
    # Si el usuario ya está logueado de forma válida, lo redirigimos al calendario
    try:
        from app.nucleo.sesion import obtener_token_cookie
        token = obtener_token_cookie(request)
        if token:
            from app.nucleo.cls_identidad import obtener_gestor_identidad
            usuario, rol = obtener_gestor_identidad().extraer_identidad(token)
            if usuario:
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url="/ui/cronograma", status_code=302)
    except Exception:
        pass

    return templates.TemplateResponse(request, "frm_login.html")


@router.get("/usuarios", response_class=HTMLResponse)
def pagina_listado_usuarios(request: Request, usuario=Depends(para_modulo("usuarios", "ver"))):
    return render_crud_page(request, template="crud_page.html", descriptor=usuarios_descriptor, ui_base="/ui/usuarios", usuario=usuario, modulo="usuarios")


@router.get("/clientes", response_class=HTMLResponse)
def pagina_listado_clientes(request: Request, usuario=Depends(para_modulo("clientes", "ver"))):
    return render_crud_page(request, template="crud_page.html", descriptor=clientes_descriptor, ui_base="/ui/clientes", usuario=usuario, modulo="clientes")


@router.get("/servicios", response_class=HTMLResponse)
def pagina_listado_servicios(request: Request, usuario=Depends(para_modulo("servicios", "ver"))):
    return render_crud_page(request, template="crud_page.html", descriptor=servicios_descriptor, ui_base="/ui/servicios", usuario=usuario, modulo="servicios")


@router.get("/proveedores", response_class=HTMLResponse)
def pagina_listado_proveedores(request: Request, usuario=Depends(para_modulo("proveedores", "ver"))):
    return render_crud_page(request, template="crud_page.html", descriptor=proveedores_descriptor, ui_base="/ui/proveedores", usuario=usuario, modulo="proveedores")


@router.get("/cotizaciones", response_class=HTMLResponse)
def pagina_listado_cotizaciones(request: Request, usuario=Depends(para_modulo("cotizaciones", "ver"))):
    return render_crud_page(request, template="crud_page.html", descriptor=cotizaciones_descriptor, ui_base="/ui/cotizaciones", usuario=usuario, modulo="cotizaciones")


@router.get("/ordenes-trabajo", response_class=HTMLResponse)
def pagina_listado_ordenes(request: Request, usuario=Depends(para_modulo("ordenes_trabajo", "ver"))):
    return render_crud_page(request, template="crud_page.html", descriptor=ordenes_descriptor, ui_base="/ui/ordenes-trabajo", usuario=usuario, modulo="ordenes_trabajo")


@router.get("/servicios-proveedores", response_class=HTMLResponse)
def pagina_servicios_proveedores(request: Request, usuario=Depends(para_modulo("servicios_proveedores", "ver"))):
    return render_crud_page(request, template="crud_page.html", descriptor=servicios_proveedores_descriptor, ui_base="/ui/servicios-proveedores", usuario=usuario, modulo="servicios_proveedores")

@router.get("/ordenes-compra", response_class=HTMLResponse)
def pagina_ordenes_compra(request: Request, usuario=Depends(para_modulo("ordenes_compra", "ver"))):
    return render_crud_page(request, template="crud_page.html", descriptor=ordenes_compra_descriptor, ui_base="/ui/ordenes-compra", usuario=usuario, modulo="ordenes_compra")

@router.get("/viaticos", response_class=HTMLResponse)
def pagina_listado_viaticos(request: Request, usuario=Depends(para_modulo("viaticos", "ver"))):
    return render_crud_page(request, template="crud_page.html", descriptor=viaticos_descriptor, ui_base="/ui/viaticos", usuario=usuario, modulo="viaticos")
