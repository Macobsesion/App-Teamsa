from sqlmodel import Session, select
from app.nucleo.base_datos import obtener_motor
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.cotizaciones.cotizaciones_servicios import ServicioCotizaciones
from decimal import Decimal

def test():
    engine = obtener_motor()
    with Session(engine) as session:
        cot = session.exec(select(Cotizacion).order_by(Cotizacion.id.desc())).first()
        if not cot:
            print('No hay cotizaciones.')
            return

        print(f'Test: Procesar conceptos en Cotizacion {cot.id} ({cot.numero})')
        
        # Simular payload del frontend
        payload = {
            "servicios": [
                {
                    "servicio_id": 1,
                    "descripcion": "Servicio Normal Simulado",
                    "codigo_sat": "00000000",
                    "unidad": "pieza",
                    "cantidad": 1,
                    "precio_unitario": 500.0,
                    "descuento_porcentaje": 0
                }
            ]
        }
        
        try:
            servicio = ServicioCotizaciones(session)
            servicio._procesar_conceptos_y_viaticos(cot, payload, "test")
            session.commit()
            print("Guardado exitoso!")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    test()
