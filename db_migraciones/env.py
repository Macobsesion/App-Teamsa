from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from sqlmodel import SQLModel  # type: ignore
from app.nucleo.configuracion import settings

# Importar todos los modelos para asegurar que se registren en SQLModel.metadata
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.modulos.clientes.clientes_modelo import Cliente
from app.modulos.proveedores.proveedores_modelo import Proveedor
from app.modulos.servicios.servicios_modelo import Servicio
from app.modulos.servicios_proveedores.servicios_proveedores_modelo import ServicioProveedor
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo, ConceptoOrdenTrabajo
from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra, DetalleOrdenCompra
from app.modulos.viaticos.viaticos_modelo import Viatico

target_metadata = SQLModel.metadata

# Configurar explícitamente la URL usando la configuración de la app
config.set_main_option("sqlalchemy.url", str(settings.SQLALCHEMY_DATABASE_URI))

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
