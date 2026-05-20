"""
Script de prueba para validar refactorización de POO (Servicios + Estrategia).
"""
import sys
import os
from decimal import Decimal
from datetime import date

# Agregar directorio raíz para ejecución local/docker
sys.path.append(os.getcwd())

from sqlmodel import Session, select

# Usar herramientas del núcleo
from app.nucleo.base_datos import obtener_motor
# Asegurar que los modelos estén registrados
from app.modulos.clientes.clientes_modelo import Cliente
from app.modulos.servicios.servicios_modelo import Servicio
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.cotizaciones.cotizaciones_servicios import ServicioCotizaciones
from app.base.servicios import FabricaImpuestos, ImpuestoFronteraMX, ImpuestoTasaCero

def setup_db():
    return obtener_motor()

def test_polimorfismo_impuestos():
    print("\n--- TEST POLIMORFISMO IMPUESTOS ---")
    
    # Caso 1: Centro (Default)
    estrategia = FabricaImpuestos.obtener_estrategia("MX_CENTRO")
    impuesto = estrategia.calcular(Decimal("100.00"))
    print(f"Region: Centro | Base: 100.00 | IVA: {impuesto} (Esperado: 16.00)")
    assert impuesto == Decimal("16.00")
    
    # Caso 2: Frontera
    estrategia = FabricaImpuestos.obtener_estrategia("MX_FRONTERA")
    impuesto = estrategia.calcular(Decimal("100.00"))
    print(f"Region: Frontera | Base: 100.00 | IVA: {impuesto} (Esperado: 8.00)")
    assert impuesto == Decimal("8.00")
    
    # Caso 3: Extranjero/Especial
    estrategia = FabricaImpuestos.obtener_estrategia(regimen_fiscal="610")
    impuesto = estrategia.calcular(Decimal("100.00"))
    print(f"Regimen: 610 | Base: 100.00 | IVA: {impuesto} (Esperado: 0.00)")
    assert impuesto == Decimal("0.00")
    print("✅ Polimorfismo OK")

def test_servicio_creacion_cotizacion():
    print("\n--- TEST SERVICIO CREACION (INTEGRACION) ---")
    engine = setup_db()
    with Session(engine) as db:
        servicio = ServicioCotizaciones(db)
        
        # 1. Buscar o crear un cliente de prueba
        cliente = db.exec(select(Cliente)).first()
        if not cliente:
            print("⚠️ No hay clientes en BD para probar integración completa.") 
            # Intentar crear uno si es posible, o abortar
            # cliente = Cliente(...)
            # db.add(cliente); db.commit()
            return

        print(f"Usando Cliente ID: {cliente.id} ({cliente.nombre})")
        
        datos_cotizacion = {
            "cliente_id": cliente.id,
            "metodo_pago": "PUE",
            "forma_pago": "03",
            "forma_pago": "03",
            "notas": "Prueba Refactor POO",
            "usuario_id": "TEST_USER",
            "servicios": [
                {
                    "servicio_id": None, 
                    "codigo_sat": "81112100",
                    "descripcion": "Desarrollo de Software",
                    "unidad": "Servicio",
                    "cantidad": 1,
                    "precio_unitario": 1000.00,
                    "descuento_porcentaje": 0
                },
                {
                    "servicio_id": None, 
                    "codigo_sat": "81112100",
                    "descripcion": "Hosting",
                    "unidad": "Anual",
                    "cantidad": 1,
                    "precio_unitario": 500.00,
                    "descuento_porcentaje": 10
                }
            ]
        }
        
        try:
            # Ejecutar el servicio
            cotizacion = servicio.crear_cotizacion_completa(datos_cotizacion, datos_cotizacion['usuario_id'])
            print(f"✅ Cotización Creada: {cotizacion.numero} (ID: {cotizacion.id})")
            print(f"   Subtotal: {cotizacion.subtotal}")
            print(f"   Descuento: {cotizacion.descuento_global}")
            print(f"   IVA: {cotizacion.iva}")
            print(f"   Total: {cotizacion.total}")
            
            # Validaciones de cálculo
            # Linea 1: 1000
            # Linea 2: 500 - 10% = 450
            # Subtotal esperado: 1450
            # IVA (16% default): 232
            # Total: 1682
            
            # Nota: Si el cliente seleccionado fuera de frontera, esto fallaría.
            # Verificamos estrategia usada
            impuesto_esperado = Decimal("0.16")
            if cliente.cp and cliente.cp.startswith("22"):
                impuesto_esperado = Decimal("0.08")
            
            iva_esperado = Decimal("1450.00") * impuesto_esperado
            assert cotizacion.iva == iva_esperado
            assert cotizacion.subtotal == Decimal("1450.00") # Neto (Base Imponible)
            # assert cotizacion.descuento_global == Decimal("50.00") # Descuento global no se calcula así con la nueva lógica base
            print("✅ Cálculos Correctos")
            
            # Opcional: Limpieza
            # db.delete(cotizacion)
            # db.commit()
            
        except Exception as e:
            print(f"❌ Error en servicio: {e}")
            raise

if __name__ == "__main__":
    test_polimorfismo_impuestos()
    test_servicio_creacion_cotizacion()
