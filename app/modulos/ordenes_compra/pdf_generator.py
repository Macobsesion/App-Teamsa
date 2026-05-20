from app.base.generador_pdf import GeneradorPDF, GeneradorPDFDocumento
from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra
from app.modulos.proveedores.proveedores_modelo import Proveedor
from app.base.utilidades_fecha import formatear_fecha_español
from sqlmodel import Session


class GeneradorPDFOrdenCompra(GeneradorPDFDocumento):
    """Generador especializado para Órdenes de Compra."""
    plantilla = "pdf/orden_compra.html"

    def _obtener_entidad(self, entidad_id: int) -> OrdenCompra:
        return self.db.get(OrdenCompra, entidad_id)

    def _construir_contexto(self, entidad: OrdenCompra) -> dict:
        proveedor = self.db.get(Proveedor, entidad.proveedor_id)

        return {
            "orden": entidad,
            "proveedor": proveedor,
            "detalles": entidad.detalles,
            "fecha_emision_formateada": formatear_fecha_español(entidad.fecha_emision) if entidad.fecha_emision else "N/A",
            "fecha_entrega_formateada": formatear_fecha_español(entidad.fecha_entrega_estimada) if entidad.fecha_entrega_estimada else "Por Confirmar",
        }


def generar_pdf_orden_compra(orden_id: int, db: Session) -> bytes:
    """Genera el PDF de una orden de compra."""
    return GeneradorPDFOrdenCompra(db).generar(orden_id)
