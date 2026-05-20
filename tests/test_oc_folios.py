import pytest
from datetime import date
from sqlmodel import Session, select
from app.nucleo.base_datos import obtener_motor
from app.modulos.ordenes_compra.ordenes_compra_repositorio import RepositorioOrdenCompra
from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra
from app.modulos.proveedores.proveedores_modelo import Proveedor

def test_folio_oc_formato_mensual():
    """Valida que el folio de OC siga el formato OC-YYMMNN."""
    engine = obtener_motor()
    with Session(engine) as session:
        # 1. Obtener un proveedor para la prueba
        proveedor = session.exec(select(Proveedor)).first()
        if not proveedor:
            pytest.skip("No hay proveedores en la base de datos para realizar la prueba.")

        repo = RepositorioOrdenCompra(session)
        
        # 2. Datos de la OC de prueba
        datos_oc = {
            "proveedor_id": proveedor.id,
            "estado": "borrador",
            "fecha_emision": date.today(),
            "metodo_pago": "PPD",
            "forma_pago": "99",
            "creado_por": "ai-tester",
        }
        
        nueva_oc = repo.crear(datos_oc)
        
        try:
            # Validar formato OC-YYMMNN
            esperado_prefijo = "OC-"
            fecha_str = date.today().strftime("%y%m")
            
            assert nueva_oc.folio.startswith(f"{esperado_prefijo}{fecha_str}"), f"Folio {nueva_oc.folio} no sigue el formato esperado {esperado_prefijo}{fecha_str}XX"
            assert len(nueva_oc.folio) >= 9, "El folio es demasiado corto"
            
        finally:
            # Limpieza
            session.delete(nueva_oc)
            session.commit()

if __name__ == "__main__":
    # Para ejecución directa
    try:
        test_folio_oc_formato_mensual()
        print("✅ Prueba de folio OC exitosa.")
    except Exception as e:
        print(f"❌ Prueba de folio OC fallida: {e}")
