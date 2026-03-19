"""Router y Descriptor CRUD para Servicios de Proveedor."""
from app.base.descriptor_crud import DescriptorCRUD, ConfiguracionUI
from app.base.factory_modulo import crear_modulo_crud_estandar
from app.base.validaciones import generador_validador_unicidad

from app.modulos.servicios_proveedores.servicios_proveedores_modelo import ServicioProveedor
from app.modulos.servicios_proveedores.servicios_proveedores_esquemas import (
    ServicioProveedorCreate, ServicioProveedorUpdate, ServicioProveedorRead
)
from app.modulos.servicios_proveedores.servicios_proveedores_repositorio import RepositorioServicioProveedor
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.modulos.proveedores.proveedores_repositorio import RepositorioProveedor

# Configuración del Descriptor
descriptor = DescriptorCRUD[
    RepositorioServicioProveedor, 
    ServicioProveedorCreate, 
    ServicioProveedorUpdate, 
    ServicioProveedorRead, 
    UsuarioIdentity
](
    label="Catálogo de Compra",
    base_url="/api/servicios-proveedores",
    repo_factory=RepositorioServicioProveedor,
    schema_read=ServicioProveedorRead,
    schema_create=ServicioProveedorCreate,
    schema_update=ServicioProveedorUpdate,
    campos_editables=[
        "proveedor_id", "codigo_sku", "descripcion", 
        "descripcion_detallada", "costo_unitario", "moneda", 
        "unidad", "activo"
    ],
    validar_unicidad=generador_validador_unicidad("codigo_sku", "El SKU '{valor}' ya existe para otro servicio"),
    filtros_permitidos={"proveedor_id", "activo"},
    campo_busqueda="descripcion",
    # Configuración UI
    config_ui=ConfiguracionUI(
        selectores={
            "proveedor_id": {
                "label": "Proveedor",
                "source_url": "/api/proveedores",
                "value_field": "id",
                "label_field": "nombre"
            }
        },
        topic="servicios_proveedores",
        columnas_incluir=["codigo_sku", "descripcion", "proveedor_id", "costo_unitario"]
    )
)

router = crear_modulo_crud_estandar(
    descriptor=descriptor,
    nombre_modulo="servicios_proveedores",
    include_select_endpoint=True,
    select_fields=["id", "codigo_sku", "descripcion", "unidad", "costo_unitario", "moneda", "proveedor_id", "activo"],
)

