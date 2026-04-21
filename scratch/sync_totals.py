from app.nucleo.base_datos import sesion_bd
from app.modulos.cotizaciones.cotizaciones_modelo import ConceptoCotizacion, Cotizacion
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion
from sqlmodel import select

print("Iniciando sincronización de importes...")
with sesion_bd() as session:
    repo = RepositorioCotizacion(session)
    
    # 1. Corregir importes de conceptos
    conceptos = session.exec(select(ConceptoCotizacion)).all()
    count_c = 0
    for c in conceptos:
        c.calcular_importe()
        session.add(c)
        count_c += 1
    session.commit()
    print(f"Se actualizaron {count_c} conceptos.")
    
    # 2. Corregir totales de cotizaciones
    cots = session.exec(select(Cotizacion.id)).all()
    count_q = 0
    for cid in cots:
        repo.recalcular_totales(cid)
        count_q += 1
    session.commit()
    print(f"Se recalcularon {count_q} cotizaciones.")

print("Sincronización completada con éxito.")
