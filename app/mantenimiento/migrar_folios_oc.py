"""Script de mantenimiento para migrar folios de OC al nuevo formato OC-YYMMNN."""
import argparse
from sqlmodel import Session, select
from app.nucleo.base_datos import obtener_motor
# Importar todos los modelos para resolver dependencias de SQLAlchemy
from app.modulos.usuarios.usuarios_modelo import Usuario 
from app.modulos.clientes.clientes_modelo import Cliente
from app.modulos.servicios.servicios_modelo import Servicio
from app.modulos.servicios_proveedores.servicios_proveedores_modelo import ServicioProveedor
from app.modulos.proveedores.proveedores_modelo import Proveedor 
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra
from app.modulos.ordenes_compra.ordenes_compra_repositorio import RepositorioOrdenCompra

def migrar_folios_oc(commit: bool = False):
    from app.nucleo.base_datos import crear_tablas, obtener_motor
    crear_tablas() # Carga todos los modelos en el registro de SQLModel
    
    engine = obtener_motor()
    with Session(engine) as db:
        repo = RepositorioOrdenCompra(db)
        # 1. Obtener todas las OCs
        statement = select(OrdenCompra).order_by(OrdenCompra.fecha_emision, OrdenCompra.id)
        ocs = db.exec(statement).all()
        
        print(f"Iniciando migración de folios OC... (Commit: {commit})")
        print(f"Encontradas {len(ocs)} órdenes de compra para procesar.")

        # 2. FASE DE LIMPIEZA: Asignar folios temporales para evitar colisiones Unique
        # Esto es vital si algunos ya tienen el formato nuevo o hay IDs solapados.
        print("Fase 1: Asignando folios temporales...")
        for oc in ocs:
            oc.folio = f"TEMP-MIGRATE-{oc.id}"
            db.add(oc)
        db.flush() # Sincroniza con la BD sin commitear aún si no se pide

        # 3. FASE DE ASIGNACIÓN: Generar folios según la nueva estrategia
        print("Fase 2: Asignando nuevos folios OC-YYMMNN...")
        processed_count = 0
        from collections import defaultdict
        contadores_mensuales = defaultdict(int)

        for oc in ocs:
            viejo_folio = oc.folio
            mes_key = oc.fecha_emision.strftime("%Y-%m")
            contadores_mensuales[mes_key] += 1
            secuencia = contadores_mensuales[mes_key]
            
            from app.base.folios import EstrategiaFolioMensual
            estrategia = EstrategiaFolioMensual()
            nuevo = estrategia.generar(prefijo="OC", fecha=oc.fecha_emision, secuencia=secuencia)
            
            oc.folio = nuevo
            print(f"ID {oc.id} ({oc.fecha_emision}): {viejo_folio} -> {nuevo}")
            processed_count += 1
            db.add(oc)
        
        if commit:
            print(f"Guardando cambios en {processed_count} registros...")
            db.commit()
            print("Migración completada exitosamente.")
        else:
            print("\nMODO SIMULACIÓN: No se guardaron cambios.")
            db.rollback()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true", help="Aplicar cambios a la base de datos")
    args = parser.parse_args()
    migrar_folios_oc(commit=args.commit)
