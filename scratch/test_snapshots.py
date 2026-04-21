
import sys
import os
from decimal import Decimal

# Añadir el path del proyecto para poder importar los módulos
sys.path.append("/home/teamsa/htdocs/teamsa.com.mx/teamsa-app-dev")

from app.base.mixins_snapshots import SnapshotClienteMixin, SnapshotProveedorMixin
from app.base.valores import Direccion

class MockCliente:
    def __init__(self):
        self.nombre = "Cliente de Prueba"
        self.rfc = "PRUE000000XXX"
        self.direccion = "Calle 123"
        self.ciudad = "Ciudad de Prueba"
        self.cp = "12345"
        self.telefono = "555-1234"
        self.email = "prueba@correo.com"
        self.email_facturacion = "factura@correo.com"

class MockDocumento(SnapshotClienteMixin):
    def __init__(self):
        self.cliente_id = 1

def test_snapshot_cliente():
    print("Probando SnapshotClienteMixin...")
    cliente = MockCliente()
    doc = MockDocumento()
    
    doc.capturar_datos_cliente(cliente)
    
    assert doc.cliente_nombre == "Cliente de Prueba"
    assert doc.cliente_rfc == "PRUE000000XXX"
    assert doc.cliente_direccion == "Calle 123"
    assert doc.cliente_email == "factura@correo.com"
    
    print("✓ Campos poblados correctamente.")
    
    print(f"Dirección VO: {doc.direccion_cliente_vo}")
    assert str(doc.direccion_cliente_vo) == "Calle 123, Ciudad de Prueba, 12345"
    print("✓ Value Object de Dirección funcionando.")
    
    # Probar setter de VO
    nueva_dir = Direccion(calle="Nueva Calle 456", ciudad="Otra Ciudad", cp="54321")
    doc.direccion_cliente_vo = nueva_dir
    assert doc.cliente_direccion == "Nueva Calle 456"
    assert doc.cliente_cp == "54321"
    print("✓ Setter de Value Object funcionando.")

if __name__ == "__main__":
    try:
        test_snapshot_cliente()
        print("\nPruebas completadas exitosamente.")
    except Exception as e:
        print(f"\nError en las pruebas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
