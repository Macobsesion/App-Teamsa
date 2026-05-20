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
from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo, ConceptoOrdenTrabajo
from app.base.constantes import PREFIJO_NUMERO_COTIZACION, PREFIJO_NUMERO_VIATICO

def migrar_folios_v3(dry_run=True):
    engine = obtener_motor()
    with Session(engine) as session:
        print(f"Iniciando MIGRACIÓN V3 (Versiones Compactas) (Dry Run: {dry_run})...")
        
        # --- Fase 1: Actualizar Viáticos ---
        print("\nProcesando Viáticos...")
        # Agrupamos por cotizacion_id para mantener secuencias coherentes
        stmt_cots_v = select(Viatico.cotizacion_id).distinct().where(Viatico.cotizacion_id != None)
        cots_con_viaticos = session.exec(stmt_cots_v).all()
        
        for cot_id in cots_con_viaticos:
            cot = session.get(Cotizacion, cot_id)
            if not cot or not cot.numero: continue
            
            # 'COT-260307-B' -> '260307B'
            base_folio = cot.numero.replace("COT-", "").replace("-", "")
            
            viaticos = session.exec(select(Viatico).where(Viatico.cotizacion_id == cot_id).order_by(Viatico.id)).all()
            for i, v in enumerate(viaticos, 1):
                nuevo_folio = f"{PREFIJO_NUMERO_VIATICO}-{base_folio}-{i}"
                if v.folio != nuevo_folio:
                    print(f"  Viático {v.id}: {v.folio} -> {nuevo_folio}")
                    v.folio = nuevo_folio
                    session.add(v)

        # --- Fase 2: Actualizar OTs ---
        print("\nProcesando OTs...")
        stmt_cots_o = select(OrdenTrabajo.cotizacion_id).distinct().where(OrdenTrabajo.cotizacion_id != None)
        cots_con_ots = session.exec(stmt_cots_o).all()
        
        for cot_id in cots_con_ots:
            cot = session.get(Cotizacion, cot_id)
            if not cot or not cot.numero: continue
            
            base_folio = cot.numero.replace("COT-", "").replace("-", "")
            
            ots = session.exec(select(OrdenTrabajo).where(OrdenTrabajo.cotizacion_id == cot_id).order_by(OrdenTrabajo.id)).all()
            for i, o in enumerate(ots, 1):
                nuevo_folio_ot = f"OT-{base_folio}-{i}"
                if o.numero_ot != nuevo_folio_ot:
                    print(f"  OT {o.id}: {o.numero_ot} -> {nuevo_folio_ot}")
                    o.numero_ot = nuevo_folio_ot
                    session.add(o)
        
        if dry_run:
            print("\nDRY RUN: No se han guardado cambios.")
        else:
            print("\nGuardando cambios definitivos...")
            session.commit()
            print("MIGRACIÓN V3 COMPLETADA EXITOSAMENTE.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migración de folios V3 - Versiones Compactas")
    parser.add_argument("--commit", action="store_true", help="Confirmar cambios en la BD")
    args = parser.parse_args()
    
    migrar_folios_v3(dry_run=not args.commit)
