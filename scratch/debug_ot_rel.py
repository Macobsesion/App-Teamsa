
from sqlmodel import Session, select
from app.nucleo.base_datos import obtener_motor
from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo
from sqlalchemy.orm import selectinload

def debug_ots():
    motor = obtener_motor()
    with Session(motor) as session:
        statement = select(OrdenTrabajo).options(selectinload(OrdenTrabajo.cotizacion))
        results = session.exec(statement).all()
        
        print(f"Total OTs: {len(results)}")
        for ot in results:
            print(f"OT: {ot.numero_ot} | Cot ID: {ot.cotizacion_id} | Relation: {ot.cotizacion.numero if ot.cotizacion else 'NONE'}")

if __name__ == "__main__":
    debug_ots()
