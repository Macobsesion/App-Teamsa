import pytest
from app.base.excepciones import AppError, RecursoNoEncontradoError, ReglaNegocioError, PermisoDenegadoError

def test_jerarquia_excepciones():
    """Verifica la herencia correcta de excepciones."""
    err = RecursoNoEncontradoError("No existe")
    assert isinstance(err, AppError)
    assert isinstance(err, Exception)
    assert err.codigo == "NO_ENCONTRADO"

def test_regla_negocio_error():
    err = ReglaNegocioError("Saldo insuficiente")
    assert err.codigo == "REGLA_NEGOCIO"
    assert "Saldo insuficiente" in str(err)

def test_captura_generica():
    """Verifica que se puedan capturar como AppError."""
    try:
        raise PermisoDenegadoError()
    except AppError as e:
        assert e.codigo == "ACCESO_DENEGADO"
    except Exception:
        pytest.fail("Debería haber sido capturado como AppError")
