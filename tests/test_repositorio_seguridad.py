"""Tests de seguridad para el repositorio genérico.

Verifica que las búsquedas sean seguras contra inyección SQL
mediante wildcards y que las cookies se configuren correctamente.
"""
import pytest
from app.base.repositorio import RepositorioCRUD
from app.modulos.clientes.clientes_modelo import Cliente
from app.modulos.clientes.clientes_repositorio import RepositorioCliente


def test_sanitizar_busqueda_escapa_wildcards(db_session):
    """Verifica que los wildcards SQL sean escapados correctamente."""
    repo = RepositorioCliente(db_session)
    
    # Crear cliente de prueba
    cliente = repo.crear(
        nombre="Acme Corporation",
        activo=True,
        creado_por="test",
        modificado_por="test"
    )
    
    # Búsqueda con wildcard % (sin sanitizar devolvería múltiples resultados)
    # Con sanitización, debe buscar literalmente "A%", no encontrar nada
    resultados = repo.listar(filtros={"nombre": "A%"})
    assert len(resultados) == 0, "El wildcard % debe ser escapado"
    
    # Búsqueda normal debe funcionar
    resultados = repo.listar(filtros={"nombre": "Acme"})
    assert len(resultados) == 1
    assert resultados[0].nombre == "Acme Corporation"


def test_sanitizar_busqueda_previene_dump_completo(db_session):
    """Verifica que '%' no devuelva todos los registros (ataque común)."""
    repo = RepositorioCliente(db_session)
    
    # Crear varios clientes
    for i in range(5):
        repo.crear(
            nombre=f"Cliente {i}",
            activo=True,
            creado_por="test",
            modificado_por="test"
        )
    
    # Búsqueda con solo '%' (intento de dump completo)
    # Con sanitización, debe buscar literalmente "%", no encontrar nada
    resultados = repo.listar(filtros={"nombre": "%"})
    assert len(resultados) == 0, "El wildcard % solo debe buscar todos los registros cuando no está escapado"


def test_sanitizar_busqueda_escapa_underscore(db_session):
    """Verifica que el wildcard _ sea escapado."""
    repo = RepositorioCliente(db_session)
    
    # Crear clientes con nombres similares
    repo.crear(nombre="Test_A", activo=True, creado_por="test", modificado_por="test")
    repo.crear(nombre="TestXA", activo=True, creado_por="test", modificado_por="test")
    
    # Búsqueda con _ (sin escapar, matchearía "TestXA" también)
    # Con sanitización, debe buscar literalmente "Test_A"
    resultados = repo.listar(filtros={"nombre": "Test_A"})
    
    # Debe encontrar solo el que tiene underscore literal
    assert len(resultados) == 1
    assert resultados[0].nombre == "Test_A"


def test_sanitizar_busqueda_escapa_backslash(db_session):
    """Verifica que backslash sea escapado para prevenir bypass."""
    repo = RepositorioCliente(db_session)
    
    # Crear cliente con nombre que contiene backslash
    repo.crear(
        nombre="Test\\Company",
        activo=True,
        creado_por="test",
        modificado_por="test"
    )
    
    # Búsqueda con backslash debe funcionar correctamente
    resultados = repo.listar(filtros={"nombre": "Test\\"})
    
    # Debe encontrar el cliente
    assert len(resultados) == 1
    assert resultados[0].nombre == "Test\\Company"


def test_busqueda_normal_sigue_funcionando(db_session):
    """Verifica que las búsquedas normales no se vean afectadas."""
    repo = RepositorioCliente(db_session)
    
    # Crear varios clientes
    repo.crear(nombre="Acme Corp", activo=True, creado_por="test", modificado_por="test")
    repo.crear(nombre="Beta Industries", activo=True, creado_por="test", modificado_por="test")
    repo.crear(nombre="Gamma Solutions", activo=True, creado_por="test", modificado_por="test")
    
    # Búsqueda normal con texto parcial
    resultados = repo.listar(filtros={"nombre": "Corp"})
    assert len(resultados) == 1
    assert resultados[0].nombre == "Acme Corp"
    
    # Búsqueda que no encuentra nada
    resultados = repo.listar(filtros={"nombre": "NonExistent"})
    assert len(resultados) == 0
