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

from app.nucleo.base_datos import obtener_sesion_bd, obtener_motor
from app.nucleo.configuracion import settings

# 1. Configurar DB de pruebas (In-Memory SQLite para velocidad o Postgres real)
# Para integración real con lógica específica de Postgres (como JSONB o fechas),
# lo ideal es usar la misma BD pero en una transacción que se revierte.
# Aquí usaremos la conexión configurada en el entorno (Docker/Local) pero transaccional.

from app.nucleo.base_datos import obtener_sesion_bd, obtener_motor, crear_tablas
# Importar nuevos modelos para que SQLModel los registre
import app.modulos.servicios_proveedores.servicios_proveedores_modelo
import app.modulos.ordenes_compra.ordenes_compra_modelo

@pytest.fixture(scope="session")
def engine():
    """Crea el motor de base de datos para la sesión de pruebas."""
    motor = obtener_motor()
    
    # IMPORTANTE: Safeguard de seguridad
    # Nunca ejecutar drop_all() en la base de datos principal configurada en .env
    # En este entorno Docker compartido, usamos Transaction Rollback para aislar tests.
    
    import sys
    db_name = motor.url.database
    print(f"\n[SEGURIDAD] Tests corriendo contra base de datos: {db_name}")
    print("[SEGURIDAD] Modo: Transaccional (Rollback al finalizar cada test).")
    print("[SEGURIDAD] NO se borrarán tablas existentes.\n")

    # Asegurar que tablas existan (idempotente)
    crear_tablas() 
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
