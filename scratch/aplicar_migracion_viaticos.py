"""Script para aplicar migración de snapshots a viáticos."""
import sys
import os
from sqlalchemy import text
from app.nucleo.base_datos import sesion_bd

def aplicar_migracion():
    # Leer el query del archivo SQL
    sql_path = "scripts/migrate_viatico_snapshots_v2.sql"
    if not os.path.exists(sql_path):
        print(f"Error: No se encuentra {sql_path}")
        return

    with open(sql_path, "r") as f:
        query = f.read()

    print("Aplicando migración de snapshots a la tabla viaticos...")
    try:
        with sesion_bd() as db:
            # Dividir por ';' para ejecutar comandos individuales si es necesario, 
            # pero PostgreSQL permite múltiples comandos en un execute(text(...)) 
            # si se usa el driver adecuado.
            db.execute(text(query))
            db.commit()
            print("Migración aplicada exitosamente.")
    except Exception as e:
        print(f"Error al aplicar migración: {e}")
        db.rollback()

if __name__ == "__main__":
    aplicar_migracion()
