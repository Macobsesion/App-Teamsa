from decimal import Decimal
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion

def verify_mixins():
    print("Iniciando verificación de Mixins...")

    # 1. Crear concepto usando Factory Method (ahora usa MixinDetalleFinanciero)
    print("1. Creando concepto...")
    concepto = ConceptoCotizacion.crear_desde_servicio(
        servicio_id=None,
        codigo_sat="80101500",
        descripcion="Consultoría",
        unidad="Hora",
        cantidad=Decimal("10.00"),
        precio_unitario=Decimal("500.00"),
        descuento_porcentaje=Decimal("10.00") # 10% descuento
    )
    
    # Validar cálculo de importe: (10 * 500) - 10% = 5000 - 500 = 4500
    expected_importe = Decimal("4500.00")
    print(f"   Importe calculado: {concepto.importe}")
    if concepto.importe == expected_importe:
        print("   [OK] Cálculo de concepto correcto.")
    else:
        print(f"   [ERROR] Esperado {expected_importe}, obtenido {concepto.importe}")

    # 2. Crear cotización y calcular totales (ahora usa MixinDocumentoFinanciero)
    print("2. Calculando totales de cotización...")
    cotizacion = Cotizacion(cliente_id=1, numero="TEST-001", numero_version="TEST-001")
    cotizacion.conceptos.append(concepto)
    
    # Agregar otro concepto sin descuento
    concepto2 = ConceptoCotizacion.crear_desde_servicio(
        servicio_id=None,
        codigo_sat="80101501",
        descripcion="Soporte",
        unidad="Hora",
        cantidad=Decimal("2.00"),
        precio_unitario=Decimal("1000.00"),
        descuento_porcentaje=Decimal("0.00")
    )
    # Importe: 2 * 1000 = 2000
    cotizacion.conceptos.append(concepto2)
    
    # Recalcular
    cotizacion.recalcular_totales()
    
    # Validar
    # Subtotal: 5000 + 2000 = 7000 (Bruto antes de descuentos en línea, según lógica del mixin actual)
    # PERO, mi implementación de MixinDocumentoFinanciero actual suma:
    # linea_bruto = cant * precio
    # linea_desc = linea_bruto * %desc
    # subtotal = sum(linea_bruto)
    # descuento_global = sum(linea_desc)
    
    # Concepto 1: Bruto 5000, Desc 500
    # Concepto 2: Bruto 2000, Desc 0
    # Subtotal Global = 7000
    # Descuento Global = 500
    # Base = 6500
    # IVA = 6500 * 0.16 = 1040
    # Total = 6500 + 1040 = 7540
    
    print(f"   Subtotal: {cotizacion.subtotal}")
    print(f"   Descuento: {cotizacion.descuento_global}")
    print(f"   IVA: {cotizacion.iva}")
    print(f"   Total: {cotizacion.total}")
    
    assert cotizacion.subtotal == Decimal("7000.00")
    assert cotizacion.descuento_global == Decimal("500.00")
    assert cotizacion.iva == Decimal("1040.00")
    assert cotizacion.total == Decimal("7540.00")
    print("   [OK] Totales de cotización correctos.")

if __name__ == "__main__":
    try:
        verify_mixins()
        print("\n¡VERIFICACIÓN EXITOSA!")
    except AssertionError as e:
        print(f"\n[FALLO] Verificación fallida: {e}")
    except Exception as e:
        print(f"\n[ERROR] Excepción: {e}")
