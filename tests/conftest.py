"""
Configuración global de tests y fixtures.
"""
import pytest
from typing import Iterator
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.main
# Intentar acceder a la variable app dentro de main
try:
    application = app.main.app
except AttributeError:
    print("ERROR: app.main no tiene atributo 'app'")
    application = None

from app.nucleo.base_datos import obtener_sesion_bd, obtener_motor, crear_tablas
# Importar nuevos modelos para que SQLModel los registre
import app.modulos.servicios_proveedores.servicios_proveedores_modelo
import app.modulos.ordenes_compra.ordenes_compra_modelo

@pytest.fixture(scope="session")
def engine():
    """Crea el motor de base de datos para la sesión de pruebas con DB exclusiva."""
    from sqlalchemy import create_engine, text
    import os
    from app.nucleo.configuracion import settings
    from app.nucleo.base_datos import reiniciar_motor, obtener_motor, crear_tablas

    # 1. Conectar a postgres por defecto para crear la DB de tests
    db_name = "teamsa_test_db"
    orig_db = settings.POSTGRES_DB
    admin_url = str(settings.SQLALCHEMY_DATABASE_URI).replace(f"/{orig_db}", "/postgres")
    
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'")).scalar()
        if not exists:
            print(f"\\n[SETUP] Creando base de datos exclusiva para tests: {db_name}...")
            conn.execute(text(f"CREATE DATABASE {db_name}"))
    
    # 2. Reconfigurar la app para usar la BD de tests
    settings.POSTGRES_DB = db_name
    reiniciar_motor()
    motor = obtener_motor()
    
    print(f"\n[SEGURIDAD] Tests corriendo contra base de datos EXCLUSIVA: {motor.url.database}")
    print("[SEGURIDAD] Modo: Creación fresca desde cero y Rollback por test.")

    # Asegurar que base de tests esté limpia (Drop All solo seguro aquí)
    SQLModel.metadata.drop_all(motor)
    SQLModel.metadata.create_all(motor) 
    return motor

@pytest.fixture(scope="function")
def info_bd(engine):
    """
    Simula una transacción rollback-only para cada test.
    Esto permite usar la BD real sin ensuciarla.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Sobreescribir dependencia de FastAPI para usar esta sesión
    # Sobreescribir dependencia de FastAPI para usar esta sesión
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[obtener_sesion_bd] = lambda: session

    yield session

    session.close()
    transaction.rollback()
    connection.close()

    # Limpiar suscriptores del BusEventos para evitar acumulación entre tests
    from app.base.eventos import BusEventos
    BusEventos.limpiar()

    # Re-registrar handlers para el próximo test (la app quedó con la sesión inyectada)
    from app.modulos.ordenes.eventos import (
        EVENTO_ORDEN_CREADA, handler_actualizar_cotizacion_aceptada,
        EVENTO_ORDEN_FINALIZADA, handler_cotizacion_finalizada,
        EVENTO_ORDEN_CANCELADA, handler_cotizacion_revertir_a_enviada,
    )
    BusEventos.suscribir(EVENTO_ORDEN_CREADA, handler_actualizar_cotizacion_aceptada)
    BusEventos.suscribir(EVENTO_ORDEN_FINALIZADA, handler_cotizacion_finalizada)
    BusEventos.suscribir(EVENTO_ORDEN_CANCELADA, handler_cotizacion_revertir_a_enviada)

    # Limpiar override
    fastapi_app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def client(info_bd):
    """Cliente de pruebas con sesión inyectada."""
    return TestClient(application)

@pytest.fixture(scope="function")
def session(info_bd):
    """Alias para la sesión de DB, útil para factories."""
    return info_bd

from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity
from app.rutas.dependencias import dp_usuario_actual

@pytest.fixture(scope="function")
def admin_client(client):
    """
    Cliente de pruebas autenticado como administrador.
    Simplifica los tests que requieren permisos.
    """
    admin_user = UsuarioIdentity(usuario="admin", rol="admin")
    
    # Override de la dependencia de autenticación
    # Accedemos a la app a través del client.app
    client.app.dependency_overrides[dp_usuario_actual] = lambda: admin_user
    
    yield client
    
    # Limpieza
    client.app.dependency_overrides.pop(dp_usuario_actual, None)
