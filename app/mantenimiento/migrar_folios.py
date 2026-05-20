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
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.viaticos.viaticos_modelo import Viatico
from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo
from app.base.constantes import PREFIJO_NUMERO_COTIZACION, PREFIJO_NUMERO_VIATICO

def migrar_folios(dry_run=True):
    engine = obtener_motor()
    with Session(engine) as session:
        print("Iniciando migración de folios...")
        
        # 1. Obtener todas las cotizaciones "madre" (sin cotizacion_original_id)
        # Ordenadas por fecha_emision e ID para mantener coherencia cronológica
        stmt_madres = select(Cotizacion).where(Cotizacion.cotizacion_original_id == None).order_by(Cotizacion.fecha_emision, Cotizacion.id)
        madres = session.exec(stmt_madres).all()
        
        print(f"Encontradas {len(madres)} cotizaciones madre para procesar.")
        
        contadores_mensuales = {} # {(anio, mes): contador}
        
        for madre in madres:
            anio_mes = (madre.fecha_emision.year, madre.fecha_emision.month)
            if anio_mes not in contadores_mensuales:
                contadores_mensuales[anio_mes] = 1
            else:
                contadores_mensuales[anio_mes] += 1
            
            secuencia = contadores_mensuales[anio_mes]
            prefijo_fecha = madre.fecha_emision.strftime("%y%m")
            nuevo_numero_madre = f"{PREFIJO_NUMERO_COTIZACION}-{prefijo_fecha}{str(secuencia).zfill(2)}"
            
            old_numero = madre.numero
            madre.numero = nuevo_numero_madre
            madre.numero_version = nuevo_numero_madre
            session.add(madre)
            
            print(f"Cotización {madre.id}: {old_numero} -> {nuevo_numero_madre}")
            
            # --- Fase 2: Actualizar Versiones de esta madre ---
            stmt_versiones = select(Cotizacion).where(Cotizacion.cotizacion_original_id == madre.id).order_by(Cotizacion.id)
            versiones = session.exec(stmt_versiones).all()
            for v in versiones:
                v.numero = f"{nuevo_numero_madre}-{v.version_letra}"
                v.numero_version = v.numero
                session.add(v)
            
            # --- Fase 3: Actualizar Viáticos ---
            # 'COT-260401' -> '260401'
            base_folio = nuevo_numero_madre.replace("COT-", "")
            
            stmt_viaticos = select(Viatico).where(Viatico.cotizacion_id == madre.id).order_by(Viatico.id)
            viaticos = session.exec(stmt_viaticos).all()
            for i, viatico in enumerate(viaticos, 1):
                viatico.folio = f"{PREFIJO_NUMERO_VIATICO}-{base_folio}-{i}"
                session.add(viatico)
            
            # --- Fase 4: Actualizar OTs ---
            stmt_ots = select(OrdenTrabajo).where(OrdenTrabajo.cotizacion_id == madre.id).order_by(OrdenTrabajo.id)
            ots = session.exec(stmt_ots).all()
            for i, ot in enumerate(ots, 1):
                ot.numero_ot = f"OT-{base_folio}-{i}"
                session.add(ot)
        
        if dry_run:
            print("DRY RUN: Los cambios NO han sido guardados.")
        else:
            print("Guardando cambios...")
            session.commit()
            print("Migración completada exitosamente.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migración de folios")
    parser.add_argument("--commit", action="store_true", help="Confirmar cambios en la BD")
    args = parser.parse_args()
    
    migrar_folios(dry_run=not args.commit)
