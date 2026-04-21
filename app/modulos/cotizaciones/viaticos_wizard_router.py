"""
Sub-router para gestionar viáticos dentro del contexto de Cotizaciones (UI).
Esto resuelve los errores 404 al intentar cargar /ui/cotizaciones/viaticos/filas.
"""
from fastapi import APIRouter
from app.modulos.viaticos.viaticos_modelo import Viatico
from app.modulos.viaticos.viaticos_esquemas import ViaticoCreate, ViaticoUpdate, ViaticoRead
from app.modulos.viaticos.viaticos_repositorio import RepositorioViatico
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.base.descriptor_crud import DescriptorCRUD, ConfiguracionUI
from app.base.factory_modulo import crear_modulo_crud_estandar

# Re-utilizamos el descriptor pero con el prefijo deseado por el frontend del Wizard/Detalle
descriptor_vinculado = DescriptorCRUD[Viatico, ViaticoCreate, ViaticoUpdate, ViaticoRead, UsuarioIdentity](
    label="Viáticos Vinculados",
    base_url="/api/viaticos", # La API sigue siendo la misma
    repo_factory=RepositorioViatico,
    schema_read=ViaticoRead,
    schema_create=ViaticoCreate,
    schema_update=ViaticoUpdate,
    campos_editables={
        "proyecto", "origen", "destino", "personas", "dias",
        "costo_transporte", "costo_alojamiento", "costo_alimentos", "costo_otros",
        "tipo_transporte", "estado"
    },
    config_ui=ConfiguracionUI(
        columnas_incluir=["folio", "proyecto", "total", "estado"],
    )
)

# Creamos solo el router UI para evitar duplicar endpoints de API
router_ui = crear_modulo_crud_estandar(
    descriptor=descriptor_vinculado,
    nombre_modulo="viaticos",
    prefix_override="/ui/cotizaciones/viaticos" # <--- Aquí está la clave del 404
).router_ui
