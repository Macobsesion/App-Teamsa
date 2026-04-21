"""Router y descriptor CRUD para clientes."""
from app.base.descriptor_crud import DescriptorCRUD, ConfiguracionUI
from app.base.factory_modulo import crear_modulo_crud_estandar
from app.base.validaciones import generador_validador_unicidad
from app.modulos.clientes.clientes_esquemas import ClienteRead, ClienteCreate, ClienteUpdate
from app.modulos.clientes.clientes_repositorio import RepositorioCliente
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.base.catalogos import ESTADOS_MEXICO


# ---------- Descriptor ----------
descriptor = DescriptorCRUD[RepositorioCliente, ClienteCreate, ClienteUpdate, ClienteRead, UsuarioIdentity](
    label="Clientes",
    base_url="/api/clientes",
    repo_factory=RepositorioCliente,
    schema_read=ClienteRead,
    schema_create=ClienteCreate,
    schema_update=ClienteUpdate,
    campos_editables={
        "nombre", "rfc", "razon_social", "contacto", "email",
        "telefono", "direccion", "ciudad", "cp", "activo", "notas"
    },
    validar_unicidad=generador_validador_unicidad("nombre", "Ya existe un cliente con el nombre '{valor}'"),
    filtros_permitidos={"activo"},
    campo_busqueda="nombre",
    config_ui=ConfiguracionUI(
        columnas_incluir=["nombre", "rfc", "contacto", "email", "activo"],
        columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
        selectores={"ciudad": ESTADOS_MEXICO}
    )
)


router = crear_modulo_crud_estandar(
    descriptor=descriptor,
    nombre_modulo="clientes",
    include_select_endpoint=True,
    select_fields=["id", "nombre", "rfc", "email", "activo"],
)
