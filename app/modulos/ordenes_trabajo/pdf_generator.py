from app.base.generador_pdf import GeneradorPDF, GeneradorPDFDocumento
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.base.utilidades_fecha import formatear_fecha_español
from sqlmodel import Session


class GeneradorPDFOrdenTrabajo(GeneradorPDFDocumento):
    """Generador especializado para Órdenes de Trabajo."""
    plantilla = "pdf/orden.html"

    def _obtener_entidad(self, entidad_id: int) -> OrdenTrabajo:
        return self.db.get(OrdenTrabajo, entidad_id)

    def _construir_contexto(self, entidad: OrdenTrabajo) -> dict:
        cotizacion = self.db.get(Cotizacion, entidad.cotizacion_id)
        
        # Filtrar conceptos que son viáticos para que no aparezcan en el PDF (solicitud usuario)
        conceptos_ot = [c for c in entidad.conceptos if not (c.concepto_cotizacion and c.concepto_cotizacion.viatico_id)]

        return {
            "ot": entidad,
            "cotizacion": cotizacion,
            "conceptos": conceptos_ot,
            "fecha_programada_fmt": formatear_fecha_español(entidad.fecha_programada),
        }


def generar_pdf_orden(orden_id: int, db: Session) -> bytes:
    """Genera el PDF de una Orden de Trabajo."""
    return GeneradorPDFOrdenTrabajo(db).generar(orden_id)

