import pytest
from datetime import date
from sqlmodel import Session
from app.modulos.ordenes.dependencias import obtener_generador_folios, obtener_repo_ordenes
from app.modulos.ordenes.ordenes_repositorio import RepositorioOrden
from app.base.folios import GeneradorFolio

# Mocks
class MockGeneradorFolio:
    def generar(self, prefijo: str, id_entidad: int, fecha: date) -> str:
        return f"MOCK-{id_entidad}"

def test_dependency_override_repo():
    """
    Prueba que podemos inyectar un generador diferente al repositorio
    sin cambiar el código del repositorio.
    """
    # 1. Crear dependencia mockeada
    mock_generador = MockGeneradorFolio()
    
    # 2. Instanciar repo inyectando el mock manual (Unit Test puro)
    # (En integración con FastAPI usariamos app.dependency_overrides)
    db_mock = "DB_SESSION_MOCK" # No necesitamos DB real para este unit test de estructura
    repo = RepositorioOrden(db_mock, generador_folio=mock_generador) # type: ignore
    
    # 3. Verificar que el repo usa el mock
    folio = repo.generador_folio.generar("X", 99, date.today())
    assert folio == "MOCK-99"

def test_factory_returns_configured_repo():
    """
    Verifica que el factory 'obtener_repo_ordenes' ensambla bien.
    """
    # Simulamos lo que hace FastAPI: resolver dependencias y llamar al factory
    db_mock = "DB_SESSION"
    generador_real = obtener_generador_folios()
    
    repo = obtener_repo_ordenes(db=db_mock, generador=generador_real) # type: ignore
    
    assert isinstance(repo, RepositorioOrden)
    assert repo.db == db_mock
    assert repo.generador_folio == generador_real
