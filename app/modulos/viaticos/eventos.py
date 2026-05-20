from sqlmodel import Session, select
from app.modulos.viaticos.viaticos_modelo import Viatico
from app.modulos.cotizaciones.cotizaciones_modelo import ConceptoCotizacion
import logging

logger = logging.getLogger("teamsa.viaticos.eventos")

def handler_limpiar_conceptos_por_viatico_eliminado(viatico: Viatico):
    """
    Cuando un viático es eliminado físicamente, debemos limpiar cualquier 
    ConceptoCotizacion que dependa de él y recalcular los totales de la cotización.
    """
    from app.nucleo.base_datos import sesion_bd
    
    with sesion_bd() as db:
        # 1. Buscar conceptos vinculados
        conceptos = db.exec(
            select(ConceptoCotizacion).where(ConceptoCotizacion.viatico_id == viatico.id)
        ).all()
        
        if not conceptos:
            return
            
        logger.info(f"Limpiando {len(conceptos)} conceptos por eliminación de viático {viatico.folio}")
        
        cotizaciones_a_recalcular = set()
        
        for concepto in conceptos:
            if concepto.cotizacion_id:
                cotizaciones_a_recalcular.add(concepto.cotizacion_id)
            db.delete(concepto)
            
        db.commit()
        
        # 2. Recalcular totales de las cotizaciones afectadas
        from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
        for cot_id in cotizaciones_a_recalcular:
            cot = db.get(Cotizacion, cot_id)
            if cot:
                cot.recalcular_totales()
                db.add(cot)
        
        db.commit()
