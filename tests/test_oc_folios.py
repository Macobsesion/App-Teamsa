
import sys
import os
from datetime import date

# Añadir el path del proyecto
sys.path.append(os.getcwd())

from app.nucleo.base_datos import obtener_motor
from sqlmodel import Session, select
from app.modulos.ordenes_compra.ordenes_compra_repositorio import RepositorioOrdenCompra
from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra
from app.modulos.proveedores.proveedores_modelo import Proveedor
from app.modulos.servicios_proveedores.servicios_proveedores_modelo import ServicioProveedor

def test_folio_oc():
    engine = obtener_motor()
    with Session(engine) as session:
        # 1. Obtener un proveedor para la prueba
        proveedor = session.exec(select(Proveedor)).first()
        if not proveedor:
            print("❌ No hay proveedores en la base de datos para realizar la prueba.")
            return

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
        
        print(f"--- Iniciando prueba de creación de OC ---")
        nueva_oc = repo.crear(**datos_oc)
        
        print(f"✅ OC Creada exitosamente.")
        print(f"📋 Folio asignado: {nueva_oc.folio}")
        
        # Validar formato OC-YYMMNN
        esperado_prefijo = "OC-"
        fecha_str = date.today().strftime("%y%m")
        if nueva_oc.folio.startswith(f"{esperado_prefijo}{fecha_str}"):
            print(f"✨ El formato del folio es CORRECTO.")
        else:
            print(f"❌ El formato del folio es INCORRECTO. Esperado: {esperado_prefijo}{fecha_str}XX")

        # 3. Limpieza (opcional, pero mejor dejarlo para no ensuciar dev si no es necesario)
        # session.delete(nueva_oc)
        # session.commit()
        # print("🧹 OC de prueba eliminada.")

if __name__ == "__main__":
    test_folio_oc()
