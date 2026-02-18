import pytest
from app.base.valores import Direccion
from app.modulos.clientes.clientes_modelo import Cliente

def test_direccion_vo_validacion():
    """Verifica la validación intrínseca del VO."""
    # CP inválido (letras)
    try:
        Direccion(cp="ABCDE")
        pytest.fail("Debería fallar validación de CP")
    except ValueError as e:
        assert "numérico" in str(e)

    # CP válido
    d = Direccion(cp="12345")
    assert d.cp == "12345"

def test_cliente_propiedad_compuesta():
    """Verifica que el modelo Cliente use el VO correctamente."""
    cliente = Cliente(nombre="Test Corp")
    
    # setter
    nueva_direccion = Direccion(calle="Av. Siempre Viva 742", ciudad="Springfield", cp="12345")
    cliente.direccion_vo = nueva_direccion
    
    # verificar que se setearon las columnas planas
    assert cliente.direccion == "Av. Siempre Viva 742"
    assert cliente.ciudad == "Springfield"
    assert cliente.cp == "12345"
    
    # getter
    vo_recuperado = cliente.direccion_vo
    assert isinstance(vo_recuperado, Direccion)
    assert vo_recuperado.calle == "Av. Siempre Viva 742"
    assert str(vo_recuperado) == "Av. Siempre Viva 742, Springfield, 12345"
