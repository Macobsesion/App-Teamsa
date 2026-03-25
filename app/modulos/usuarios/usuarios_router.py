"""
Usuarios: API JSON + UI HTMX usando factory pattern.

Migrado al factory pattern para reducir duplicación y simplificar mantenimiento.
"""
from typing import Any

from app.base.descriptor_crud import DescriptorCRUD, ConfiguracionUI
from app.base.factory_modulo import crear_modulo_crud_estandar
from app.base.validaciones import generador_validador_unicidad
from app.modulos.usuarios.usuarios_esquemas import (
    UsuarioCreate,
    UsuarioIdentity,
    UsuarioRead,
    UsuarioUpdatePartial,
    UsuarioUpdatePassword,
)
from app.modulos.usuarios.usuarios_repositorio import RepositorioUsuario
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.permisos import para_modulo
from app.web.jinja import get_templates


def _validar_form_creacion(datos: dict[str, object]) -> str | None:
    """Validación específica de formulario: confirmación de contraseña."""
    if datos.get("contrasena") != datos.get("confirmarContrasena"):
        return "Las contraseñas no coinciden"
    return None


# ---------- Descriptor ----------
descriptor = DescriptorCRUD[
    RepositorioUsuario,
    UsuarioCreate,
    UsuarioUpdatePartial,
    UsuarioRead,
    UsuarioIdentity,
](
    label="Usuarios",
    base_url="/api/usuarios",
    repo_factory=RepositorioUsuario,
    schema_read=UsuarioRead,
    schema_create=UsuarioCreate,
    schema_update=UsuarioUpdatePartial,
    campos_editables={
        "nombres", "rol", "correo", "contrasena", "area"
    },
    validar_unicidad=generador_validador_unicidad("usuario", "El usuario ya existe"),
    filtros_permitidos={"rol", "area"},
    campo_busqueda="nombres",
    config_ui=ConfiguracionUI(
        columnas_incluir=["usuario", "rol", "correo", "area"],
        columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion", "contrasena"},
    )
)


router_extra = APIRouter()

@router_extra.get("/ui/usuarios/password", response_class=HTMLResponse)
def form_password(id: int, request: Request, _actor=Depends(para_modulo("usuarios", "editar"))):
    """Devuelve el mini-modal HTML HTMX para cambiar la contraseña."""
    return get_templates().TemplateResponse(request, "ui/usuarios/_form_password.html", {"item_id": id})

@router_extra.post("/api/usuarios/{usuario_id}/password")
def cambiar_password(
    usuario_id: int,
    request: Request,
    contrasena: str = Form(...),
    confirmarContrasena: str = Form(...),
    db: Session = Depends(obtener_sesion_bd),
    _actor=Depends(para_modulo("usuarios", "editar"))
):
    if contrasena != confirmarContrasena:
        return get_templates().TemplateResponse(
            request,
            "ui/usuarios/_form_password.html",
            {"item_id": usuario_id, "error": "Las contraseñas no coinciden"}
        )
    
    repo = RepositorioUsuario(db)
    # El repositorio en _pre_procesar_cambios hashea la contraseña automáticamente
    payload = UsuarioUpdatePartial(contrasena=contrasena)
    repo.actualizar(usuario_id, payload.model_dump(exclude_unset=True))
    
    from fastapi.responses import HTMLResponse
    resp = HTMLResponse(f"""
      <div class="modal-header">
        <h5 class="modal-title">🔐 Contraseña Actualizada</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
      </div>
      <div class="modal-body">
        <div class="alert alert-success">✅ La contraseña fue cambiada exitosamente.</div>
      </div>
    """)
    resp.headers["HX-Trigger"] = '{{"flash": {{"texto": "Contrase\u00f1a actualizada", "tipo": "success"}}}}'
    return resp

@router_extra.get("/ui/usuarios/permisos", response_class=HTMLResponse)
def form_permisos(id: int, request: Request, db: Session = Depends(obtener_sesion_bd), _actor=Depends(para_modulo("usuarios", "editar"))):
    """Devuelve el modal con la matriz de permisos para un usuario."""
    repo = RepositorioUsuario(db)
    usuario = repo.obtener_por_id(id)
    
    modulos_disponibles = [
        {"id": "usuarios", "nombre": "Usuarios"},
        {"id": "clientes", "nombre": "Clientes"},
        {"id": "proveedores", "nombre": "Proveedores"},
        {"id": "servicios", "nombre": "Servicios Base"},
        {"id": "servicios_proveedores", "nombre": "Servicios de Proveedores"},
        {"id": "cotizaciones", "nombre": "Cotizaciones"},
        {"id": "ordenes", "nombre": "Órdenes de Trabajo"},
        {"id": "ordenes_compra", "nombre": "Órdenes de Compra"},
    ]
    
    return get_templates().TemplateResponse(
        request, 
        "ui/usuarios/_form_permisos.html", 
        {
            "item_id": id, 
            "usuario": usuario,
            "modulos": modulos_disponibles
        }
    )

@router_extra.post("/api/usuarios/{usuario_id}/permisos")
async def guardar_permisos(
    usuario_id: int,
    request: Request,
    db: Session = Depends(obtener_sesion_bd),
    _actor=Depends(para_modulo("usuarios", "editar"))
):
    """Procesa el formulario multipart y extrae las listas de checkboxes para cada permiso."""
    form_data = await request.form()
    
    # Extraer arrays de checkboxes marcados
    permisos_ver = form_data.getlist("permisos_ver")
    permisos_crear = form_data.getlist("permisos_crear")
    permisos_editar = form_data.getlist("permisos_editar")
    permisos_eliminar = form_data.getlist("permisos_eliminar")
    
    repo = RepositorioUsuario(db)
    payload = UsuarioUpdatePartial(
        permisos_ver=permisos_ver,
        permisos_crear=permisos_crear,
        permisos_editar=permisos_editar,
        permisos_eliminar=permisos_eliminar
    )
    
    repo.actualizar(usuario_id, payload.model_dump(exclude_unset=True))
    
    resp = HTMLResponse("Permisos actualizados")
    resp.headers["HX-Trigger"] = "load" 
    # Podríamos sumar un evento de flash para notificar
    resp.headers["HX-Trigger"] = '{"load": null, "flash": {"texto": "Permisos actualizados exitosamente", "tipo": "success"}}'
    return resp

# ---------- Router Combinado usando Factory ----------
router = crear_modulo_crud_estandar(
    descriptor=descriptor,
    nombre_modulo="usuarios",
    validar_form_creacion=_validar_form_creacion,
)
