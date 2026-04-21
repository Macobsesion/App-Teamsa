import sys
import os
from datetime import date
from sqlalchemy import func
from sqlmodel import Session, select, and_

# Añadir el directorio raíz al path para poder importar la app
sys.path.append(os.getcwd())

from app.nucleo.base_datos import obtener_motor
from app.modulos.clientes.clientes_modelo import Cliente
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.viaticos.viaticos_modelo import Viatico
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo, ConceptoOrdenTrabajo
from app.base.constantes import PREFIJO_NUMERO_COTIZACION, PREFIJO_NUMERO_VIATICO

def migrar_folios_v2(dry_run=True):
    engine = obtener_motor()
    with Session(engine) as session:
        print(f"Iniciando MIGRACIÓN V2 DE FOLIOS (Dry Run: {dry_run})...")
        
        # --- Fase 0: Limpieza de Huérfanos ---
        huerfanos = session.exec(select(Viatico).where(Viatico.cotizacion_id == None)).all()
        if huerfanos:
            print(f"Limpiando {len(huerfanos)} viáticos huérfanos...")
            for h in huerfanos:
                print(f"  - Marcado para eliminación: {h.folio} (ID {h.id})")
                if not dry_run:
                    session.delete(h)
        
        # --- Fase 1: Obtener Cotizaciones Madre ---
        # El folio de las cotizaciones ya fue corregido en V1, pero lo usaremos de base.
        stmt_madres = select(Cotizacion).where(Cotizacion.cotizacion_original_id == None).order_by(Cotizacion.id)
        madres = session.exec(stmt_madres).all()
        
        print(f"Procesando familias de {len(madres)} cotizaciones...")
        
        for madre in madres:
            # 1. Definir la base para los hijos: 'COT-260401' -> '260401'
            base_folio = madre.numero.replace("COT-", "")
            
            # 2. Encontrar todos los miembros de la familia (madre + versiones)
            ids_familia = [madre.id]
            stmt_versiones = select(Cotizacion.id).where(Cotizacion.cotizacion_original_id == madre.id)
            ids_familia.extend(session.exec(stmt_versiones).all())
            
            # --- Fase 3: Actualizar Viáticos de la FAMILIA ---
            stmt_viaticos = select(Viatico).where(Viatico.cotizacion_id.in_(ids_familia)).order_by(Viatico.id)
            viaticos = session.exec(stmt_viaticos).all()
            for i, viatico in enumerate(viaticos, 1):
                nuevo_folio = f"{PREFIJO_NUMERO_VIATICO}-{base_folio}-{i}"
                if viatico.folio != nuevo_folio:
                    print(f"  Viático {viatico.id}: {viatico.folio} -> {nuevo_folio} (Madre {madre.numero})")
                    viatico.folio = nuevo_folio
                    session.add(viatico)
            
            # --- Fase 4: Actualizar OTs de la FAMILIA ---
            stmt_ots = select(OrdenTrabajo).where(OrdenTrabajo.cotizacion_id.in_(ids_familia)).order_by(OrdenTrabajo.id)
            ots = session.exec(stmt_ots).all()
            for i, ot in enumerate(ots, 1):
                nuevo_folio_ot = f"OT-{base_folio}-{i}"
                if ot.numero_ot != nuevo_folio_ot:
                    print(f"  OT {ot.id}: {ot.numero_ot} -> {nuevo_folio_ot} (Madre {madre.numero})")
                    ot.numero_ot = nuevo_folio_ot
                    session.add(ot)
        
        if dry_run:
            print("\nDRY RUN: No se han guardado cambios.")
        else:
            print("\nGuardando cambios definitivos...")
            session.commit()
            print("MIGRACIÓN V2 COMPLETADA EXITOSAMENTE.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migración de folios V2 - Soporta Versiones")
    parser.add_argument("--commit", action="store_true", help="Confirmar cambios en la BD")
    args = parser.parse_args()
    
    migrar_folios_v2(dry_run=not args.commit)
