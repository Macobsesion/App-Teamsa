"""Router y descriptor CRUD para servicios."""
from app.base.descriptor_crud import DescriptorCRUD, ConfiguracionUI
from app.base.factory_modulo import crear_modulo_crud_estandar
from app.base.validaciones import generador_validador_unicidad
from app.modulos.servicios.servicios_esquemas import ServicioRead, ServicioCreate, ServicioUpdate
from app.modulos.servicios.servicios_repositorio import RepositorioServicio
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity


# ---------- Descriptor ----------
descriptor = DescriptorCRUD[RepositorioServicio, ServicioCreate, ServicioUpdate, ServicioRead, UsuarioIdentity](
    label="Servicios",
    base_url="/api/servicios",
    repo_factory=RepositorioServicio,
    schema_read=ServicioRead,
    schema_create=ServicioCreate,
    schema_update=ServicioUpdate,
    campos_editables={
        "codigo_sat", "codigo_unidad", "clave", "descripcion",
        "tipo", "precio_base", "unidad", "activo", "notas"
    },
    validar_unicidad=generador_validador_unicidad("clave", "Ya existe un servicio con la clave '{valor}'"),
    filtros_permitidos={"activo", "tipo"},
    campo_busqueda="clave",
    config_ui=ConfiguracionUI(
        columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
    )
)


router = crear_modulo_crud_estandar(
    descriptor=descriptor,
    nombre_modulo="servicios",
    include_select_endpoint=True,
    select_fields=["id", "clave", "descripcion", "codigo_sat", "unidad", "precio_base", "activo"],
)


