"""
Script de Seed para Bases de Datos.
Utiliza las factories definidas en tests/factories.py para poblar la BD con datos iniciales.
"""
from sqlmodel import Session
from app.nucleo.base_datos import obtener_sesion_bd
from app.modulos.usuarios.usuarios_modelo import Usuario

# Importar factories.
# Nota: Como las factories usan `factory.Factory` y no `SQLAlchemyModelFactory` con session persistence automática,
# tenemos que instanciar y agregar manualmente a la sesión.
from tests.factories import (
    ClienteFactory, ProveedorFactory, ServicioFactory, 
    ServicioProveedorFactory, CotizacionFactory, ConceptoCotizacionFactory,
    OrdenCompraFactory, DetalleOrdenCompraFactory
)

def seed_database():
    session_gen = obtener_sesion_bd()
    session = next(session_gen)
    
    # 1. Validar si ya hay datos (para no duplicar si se corre 2 veces)
    # Proteccion contra ejecucion accidental
    if __name__ == "__main__":
        print("!!! ADVERTENCIA !!!")
        print("Este script insertará datos de prueba en la base de datos actual.")
        confirm = input("Escriba 'SEED' para confirmar: ")
        if confirm != "SEED":
            print("Operación cancelada.")
            return

    print("Iniciando Seed de Datos...")
    
    # --- Clientes ---
    clientes = []
    for _ in range(5):
        c = ClienteFactory()
        session.add(c)
        clientes.append(c)
    print(f"Generados {len(clientes)} clientes.")
    
    # --- Proveedores ---
    proveedores = []
    for _ in range(3):
        p = ProveedorFactory()
        session.add(p)
        proveedores.append(p)
    print(f"Generados {len(proveedores)} proveedores.")
    
    # --- Servicios (Venta) ---
    servicios_venta = []
    for _ in range(10):
        s = ServicioFactory()
        session.add(s)
        servicios_venta.append(s)
    print(f"Generados {len(servicios_venta)} servicios de venta.")

    session.commit() # Commit parcial para tener IDs
    
    # Refresh para relaciones
    for c in clientes: session.refresh(c)
    for p in proveedores: session.refresh(p)
    
    # --- Servicios (Compra - Catálogo Proveedor) ---
    servicios_compra = []
    for prov in proveedores:
        for _ in range(3): # 3 productos por proveedor
            sp = ServicioProveedorFactory(proveedor_id=prov.id)
            sp.proveedor_id = prov.id # Forzar ID por si subfactory crea uno nuevo
            session.add(sp)
            servicios_compra.append(sp)
    print(f"Generados {len(servicios_compra)} servicios de catálogo de compra.")
    
    session.commit()
    
    # --- Cotizaciones ---
    import random
    from decimal import Decimal
    
    for cli in clientes:
        # 2 cotizaciones por cliente
        for _ in range(2):
            cot = CotizacionFactory(cliente=cli)
            cot.cliente_id = cli.id
            cot.folio = cot.numero # Fix: Asignar folio explícitamente para evitar error NotNull
            session.add(cot)
            session.flush() # ID para conceptos
            
            # Conceptos
            subtotal = Decimal(0)
            for _ in range(random.randint(1, 4)):
                serv = random.choice(servicios_venta)
                concepto = ConceptoCotizacionFactory(cotizacion=cot)
                concepto.cotizacion_id = cot.id
                concepto.descripcion = serv.descripcion
                concepto.precio_unitario = serv.precio_base
                concepto.cantidad = Decimal(random.randint(1, 5))
                concepto.calcular_importe()
                session.add(concepto)
                subtotal += concepto.importe
            
            # Recalcular totales cotización
            cot.subtotal = subtotal
            cot.iva = subtotal * Decimal("0.16")
            cot.total = cot.subtotal + cot.iva
            session.add(cot)
            
    print("Generadas cotizaciones de ejemplo.")

    # --- Órdenes de Compra ---
    for prov in proveedores:
        items_prov = [s for s in servicios_compra if s.proveedor_id == prov.id]
        if not items_prov: continue
        
        # 1 Orden por proveedor
        oc = OrdenCompraFactory(proveedor=prov)
        oc.proveedor_id = prov.id
        session.add(oc)
        session.flush()
        
        subtotal_oc = Decimal(0)
        for _ in range(random.randint(1, 3)):
            item_cat = random.choice(items_prov)
            det = DetalleOrdenCompraFactory(orden=oc)
            det.orden_id = oc.id
            det.servicio_proveedor_id = item_cat.id
            det.codigo_sku = item_cat.codigo_sku
            det.descripcion = item_cat.descripcion
            det.precio_unitario = item_cat.costo_unitario
            det.cantidad = Decimal(random.randint(10, 100))
            det.calcular_importe()
            session.add(det)
            subtotal_oc += det.importe
            
        oc.subtotal = subtotal_oc
        oc.iva = subtotal_oc * Decimal("0.16")
        oc.total = oc.subtotal + oc.iva
        session.add(oc)
        
    print("Generadas órdenes de compra de ejemplo.")
    
    session.commit()
    print("Seed completado exitosamente.")

if __name__ == "__main__":
    seed_database()
