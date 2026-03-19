"""Router y descriptor CRUD para proveedores."""
from app.base.descriptor_crud import DescriptorCRUD, ConfiguracionUI
from app.base.factory_modulo import crear_modulo_crud_estandar
from app.base.validaciones import generador_validador_unicidad
from app.modulos.proveedores.proveedores_esquemas import ProveedorRead, ProveedorCreate, ProveedorUpdate
from app.modulos.proveedores.proveedores_repositorio import RepositorioProveedor
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity


# ---------- Descriptor ----------
descriptor = DescriptorCRUD[RepositorioProveedor, ProveedorCreate, ProveedorUpdate, ProveedorRead, UsuarioIdentity](
    label="Proveedores",
    base_url="/api/proveedores",
    repo_factory=RepositorioProveedor,  # Clase directa - auditoría automática
    schema_read=ProveedorRead,
    schema_create=ProveedorCreate,
    schema_update=ProveedorUpdate,
    campos_editables={
        "nombre", "rfc", "razon_social", "contacto", "email",
        "telefono", "direccion", "ciudad", "cp",
        "categoria", "activo", "notas"
    },
    validar_unicidad=generador_validador_unicidad("nombre", "Ya existe un proveedor con el nombre '{valor}'"),
    filtros_permitidos={"activo", "categoria"},
    campo_busqueda="nombre",
    config_ui=ConfiguracionUI(
        columnas_incluir=["nombre", "rfc", "contacto", "categoria", "activo"],
        columnas_excluir={"creado_por", "modificado_por", "fecha_creacion", "fecha_modificacion"},
    )
)



router = crear_modulo_crud_estandar(
    descriptor=descriptor,
    nombre_modulo="proveedores",
    include_select_endpoint=True,
    select_fields=["id", "nombre", "rfc", "categoria", "activo"],
)
