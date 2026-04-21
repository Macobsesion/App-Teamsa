from sqlmodel import Session, select, create_engine, text
from app.nucleo.base_datos import obtener_motor
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("saneamiento")

def sanear_tablas():
    motor = obtener_motor()
    
    tablas = [
        "cliente", "proveedor", "usuario", "cotizacion", 
        "orden_compra", "viatico", "servicio", "concepto_cotizacion",
        "concepto_orden_compra", "orden_trabajo", "empresa_configuracion"
    ]
    
    valores_basura = ["'none'", "'None'", "'null'", "'NULL'"]
    
    with Session(motor) as session:
        for tabla in tablas:
            try:
                # Obtener columnas de texto para la tabla
                res = session.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{tabla}' AND data_type IN ('character varying', 'text')"))
                columnas = [row[0] for row in res]
                
                if not columnas:
                    continue
                
                logger.info(f"Procesando tabla: {tabla} ({len(columnas)} columnas de texto)")
                
                for col in columnas:
                    # Ejecutar UPDATE masivo por columna
                    sql = text(f"UPDATE {tabla} SET {col} = NULL WHERE {col} IN ({', '.join(valores_basura)})")
                    result = session.execute(sql)
                    if result.rowcount > 0:
                        logger.info(f"  [!] Columna {col}: {result.rowcount} registros saneados.")
                
                session.commit()
            except Exception as e:
                logger.error(f"Error procesando tabla {tabla}: {e}")
                session.rollback()

if __name__ == "__main__":
    logger.info("Iniciando saneamiento de base de datos...")
    sanear_tablas()
    logger.info("Saneamiento completado.")
