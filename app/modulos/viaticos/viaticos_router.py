"""Router y descriptor CRUD para viáticos usando factory pattern."""
from typing import Any

from sqlmodel import Session

from app.base.descriptor_crud import DescriptorCRUD
from app.base.factory_modulo import crear_modulo_crud
from app.nucleo.base_datos import obtener_sesion_bd, obtener_motor
from app.rutas.dependencias import exigir_roles, dp_usuario_actual
from app.modulos.viaticos.viaticos_esquemas import ViaticoRead, ViaticoCreate, ViaticoUpdate
from app.modulos.viaticos.viaticos_repositorio import RepositorioViatico
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity

# Importar routers adicionales
from app.modulos.viaticos import gastos_router, pdf_router


def _campos_creacion(payload: ViaticoCreate, actor: UsuarioIdentity) -> dict[str, Any]:
    """Genera campos adicionales al crear un viático."""
    from app.base.descriptor_crud import _auditoria_creacion_default
    
    # Crear repo temporal para generar número y calcular días
    # Crear repo temporal SOLO para generar número (si aún es necesario)
    with Session(obtener_motor()) as db:
        repo_temp = RepositorioViatico(db)
        numero = repo_temp.generar_siguiente_numero()
    
    # Calcular días sin BB
    from app.modulos.viaticos.servicios import ServicioCalculadoraViatico
    dias = ServicioCalculadoraViatico.calcular_dias(payload.fecha_inicio, payload.fecha_fin)
    
    # Combinar auditoría automática con lógica de negocio
    extras = _auditoria_creacion_default(payload, actor)
    extras.update({
        "numero": numero,
        "dias": dias,
    })
    return extras


def _campos_actualizacion(payload: ViaticoUpdate, actor: UsuarioIdentity) -> dict[str, Any]:
    """Recalcula días si cambian las fechas."""
    from app.base.descriptor_crud import _auditoria_actualizacion_default
    
    extras = _auditoria_actualizacion_default(payload, actor)
    
    # Si cambian fechas, recalcular días
    if payload.fecha_inicio and payload.fecha_fin:
        from app.modulos.viaticos.servicios import ServicioCalculadoraViatico
        dias = ServicioCalculadoraViatico.calcular_dias(payload.fecha_inicio, payload.fecha_fin)
        extras["dias"] = dias
    
    return extras


# ---------- Descriptor ----------
descriptor = DescriptorCRUD[RepositorioViatico, ViaticoCreate, ViaticoUpdate, ViaticoRead, UsuarioIdentity](
    label="Viáticos",
    base_url="/api/viaticos",
    repo_factory=RepositorioViatico,
    schema_read=ViaticoRead,
    schema_create=ViaticoCreate,
    schema_update=ViaticoUpdate,
    campos_editables={
        "responsable_id", "proyecto", "cliente", "destino",
        "fecha_inicio", "fecha_fin", "estado", "notas", "observaciones"
    },
    campos_creacion_extra=_campos_creacion,
    campos_actualizacion_extra=_campos_actualizacion,
    filtros_permitidos={"estado", "responsable_id"},
    campo_busqueda="numero",
    columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
)


# ---------- Router Combinado usando Factory ----------
router = crear_modulo_crud(
    descriptor=descriptor,
    obtener_sesion=obtener_sesion_bd,
    actor_dependency=dp_usuario_actual,
    write_dependency=exigir_roles("admin"),
    tpl_filas="ui/viaticos/_filas.html",
    tpl_form="ui/viaticos/_form.html",
    routers_adicionales=[
        gastos_router.router,
        pdf_router.router,
    ],
)

