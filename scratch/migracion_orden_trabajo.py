from sqlmodel import Session, text
from app.nucleo.base_datos import obtener_motor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migracion")

def migrar_base_datos():
    motor = obtener_motor()
    
    with Session(motor) as session:
        try:
            logger.info("Renombrando tabla ordentrabajo a orden_trabajo...")
            # MySQL / Postgres / SQLite compatible syntax for rename
            session.execute(text("ALTER TABLE ordentrabajo RENAME TO orden_trabajo;"))
            
            # Verificar si hay que renombrar secuencias o índices (Postgres específico a veces)
            # En la mayoría de los casos el RENAME TO es suficiente.
            
            session.commit()
            logger.info("Migración completada con éxito.")
        except Exception as e:
            logger.error(f"Error en la migración: {e}")
            session.rollback()
            # Si falla porque ya existe o ya se renombró, lo ignoramos amigablemente
            if "already exists" in str(e) or "does not exist" in str(e):
                logger.info("La tabla parece ya haber sido renombrada o no existe la antigua.")
            else:
                raise e

if __name__ == "__main__":
    migrar_base_datos()
