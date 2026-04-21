# Herramientas para gestionar la conexión y sesiones de base de datos.
#
# Este módulo abstrae la creación del motor (engine) y provee utilidades para
# obtener sesiones como dependencias de FastAPI (yield) o como context manager
# tradicional para scripts de mantenimiento/pruebas.
from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator
import logging

from sqlmodel import SQLModel, Session, create_engine  # type: ignore

from .configuracion import settings


@lru_cache
def obtener_motor():
    """Crea (una sola vez) el motor SQLAlchemy usando la configuración actual."""
    return create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def crear_tablas() -> None:
    """Sincroniza el esquema de la base de datos con los modelos declarados."""
    # # Importación tardía para evitar ciclos al cargar modelos.
    from app.modulos.usuarios.usuarios_modelo import Usuario  # noqa: F401
    from app.modulos.clientes.clientes_modelo import Cliente  # noqa: F401
    from app.modulos.servicios.servicios_modelo import Servicio  # noqa: F401
    from app.modulos.proveedores.proveedores_modelo import Proveedor  # noqa: F401
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion  # noqa: F401
    from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo  # noqa: F401

    engine = obtener_motor()
    # PRECAUCIÓN: La creación de tablas plana está desactivada. 
    # El modelo de datos ahora es gestionado por Alembic migrations.
    # Usa: `alembic upgrade head` para sincronizar la BD.
    # SQLModel.metadata.create_all(engine)


# Alias para compatibilidad con el arranque de la aplicación
inicializar_bd = crear_tablas





def obtener_sesion_bd() -> Iterator[Session]:
    """Abre una sesión transaccional para inyectar como dependencia en FastAPI."""
    with Session(obtener_motor()) as session:
        yield session


@contextmanager
def sesion_bd() -> Iterator[Session]:
    """Context manager reutilizable (scripts, tests) para manejar sesiones manualmente."""
    with Session(obtener_motor()) as session:
        yield session


def reiniciar_motor() -> None:
    """Limpia el cache del motor; útil en pruebas o al cambiar de DSN."""
    obtener_motor.cache_clear()
