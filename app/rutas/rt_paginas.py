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
from app.modulos.viaticos.viaticos_router import descriptor as viaticos_descriptor
from app.rutas.dependencias import exigir_roles

router = APIRouter()
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "web" / "templates"
templates = get_templates()

def render_crud_page(request: Request, *, template: str, descriptor, ui_base: str, puede_editar: bool = True) -> HTMLResponse:
    """
    Renderiza una página CRUD genérica.
    - `descriptor.frontend_config()` aporta columnas (thead) y etiquetas.
    - `ui_base` es la base de rutas HTMX para filas (`/filas`) y formulario (`/form`).
    """
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "crud_config": descriptor.frontend_config(),
            "ui_base": ui_base,
            "puede_editar": puede_editar,
        },
    )

@router.get("/salud", include_in_schema=False)
def salud():
    return {"status": "ok"}

@router.get("/", response_class=HTMLResponse)
def mostrar_login(request: Request):
    # Página de autenticación (no protegida)
    return templates.TemplateResponse("frm_login.html", {"request": request})


@router.get("/error", include_in_schema=False)
def pagina_error(request: Request, status: int = 401, detail: str = "No autenticado"):
    """Ruta auxiliar para mostrar errores de API como página HTML.
    Aprovecha el handler global de HTTPException para renderizar un H1.
    """
    from fastapi import HTTPException  # import local para evitar dependencias cruzadas

    # Levanta una excepción que el handler global convertirá en HTML con <h1>
    raise HTTPException(status_code=status, detail=detail)


@router.get(
    "/usuarios",
    response_class=HTMLResponse,
    dependencies=[Depends(exigir_roles("admin"))],
)
def pagina_listado_usuarios(request: Request):
    return render_crud_page(request, template="usuarios.html", descriptor=usuarios_descriptor, ui_base="/ui/usuarios", puede_editar=True)


@router.get(
    "/clientes",
    response_class=HTMLResponse,
    dependencies=[Depends(exigir_roles("admin"))],
)
def pagina_listado_clientes(request: Request):
    return render_crud_page(request, template="crud_page.html", descriptor=clientes_descriptor, ui_base="/ui/clientes", puede_editar=True)


@router.get(
    "/servicios",
    response_class=HTMLResponse,
    dependencies=[Depends(exigir_roles("admin"))],
)
def pagina_listado_servicios(request: Request):
    return render_crud_page(request, template="crud_page.html", descriptor=servicios_descriptor, ui_base="/ui/servicios", puede_editar=True)


@router.get(
    "/proveedores",
    response_class=HTMLResponse,
    dependencies=[Depends(exigir_roles("admin"))],
)
def pagina_listado_proveedores(request: Request):
    return render_crud_page(request, template="crud_page.html", descriptor=proveedores_descriptor, ui_base="/ui/proveedores", puede_editar=True)


@router.get(
    "/cotizaciones",
    response_class=HTMLResponse,
    dependencies=[Depends(exigir_roles("admin"))],
)
def pagina_listado_cotizaciones(request: Request):
    return render_crud_page(request, template="crud_page.html", descriptor=cotizaciones_descriptor, ui_base="/ui/cotizaciones", puede_editar=True)


@router.get(
    "/viaticos",
    response_class=HTMLResponse,
    dependencies=[Depends(exigir_roles("admin"))],
)
def pagina_listado_viaticos(request: Request):
    return render_crud_page(request, template="crud_page.html", descriptor=viaticos_descriptor, ui_base="/ui/viaticos", puede_editar=True)
