from decimal import Decimal
from app.base.mixins_financieros import MixinDocumentoFinanciero, MixinDetalleFinanciero
from app.base.impuestos import ImpuestoEstandarMX, ImpuestoFronteraMX, ImpuestoTasaCero

# Clase Dummy para la prueba
class DocumentoPrueba(MixinDocumentoFinanciero):
    pass

class DetallePrueba(MixinDetalleFinanciero):
    pass

def verify_taxes():
    print("Iniciando verificación de Estrategia de Impuestos (Strategy Pattern)...")
    
    # 1. Crear items (Base imponible sera 1000)
    item = DetallePrueba(
        cantidad=Decimal("1"), 
        precio_unitario=Decimal("1000"), 
        descuento_porcentaje=Decimal("0")
    )
    detalles = [item] # Base = 1000
    
    # 2. Probar Estrategia Estándar (16%)
    doc1 = DocumentoPrueba()
    estrategia1 = ImpuestoEstandarMX()
    doc1.calcular_totales(detalles, estrategia=estrategia1) # type: ignore
    print(f"1. Estándar (16%) sobre 1000: IVA={doc1.iva}, Total={doc1.total}")
    assert doc1.iva == Decimal("160.00")
    assert doc1.total == Decimal("1160.00")
    
    # 3. Probar Estrategia Frontera (8%)
    doc2 = DocumentoPrueba()
    estrategia2 = ImpuestoFronteraMX()
    doc2.calcular_totales(detalles, estrategia=estrategia2) # type: ignore
    print(f"2. Frontera (8%) sobre 1000:  IVA={doc2.iva}, Total={doc2.total}")
    assert doc2.iva == Decimal("80.00")
    assert doc2.total == Decimal("1080.00")
    
    # 4. Probar Tasa Cero (0%)
    doc3 = DocumentoPrueba()
    estrategia3 = ImpuestoTasaCero()
    doc3.calcular_totales(detalles, estrategia=estrategia3) # type: ignore
    print(f"3. Tasa Cero (0%) sobre 1000: IVA={doc3.iva}, Total={doc3.total}")
    assert doc3.iva == Decimal("0.00")
    assert doc3.total == Decimal("1000.00")

    print("[OK] Todas las estrategias funcionaron correctamente.")

if __name__ == "__main__":
    try:
        verify_taxes()
    except AssertionError as e:
        print(f"[FALLO] Verificación fallida: {e}")
    except Exception as e:
        print(f"[ERROR] Excepción: {e}")
