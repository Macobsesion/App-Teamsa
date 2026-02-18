from sqlmodel import Session
from pathlib import Path
from fastapi.responses import Response

from app.base.generador_pdf import GeneradorPDF
from app.base.constantes import LOGO_PDF
from app.base.utilidades_fecha import formatear_fecha_español
from app.base.excepciones import RecursoNoEncontradoError

from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra
from app.modulos.proveedores.proveedores_modelo import Proveedor
from app.modulos.cotizaciones.pdf_generator import imagen_a_data_uri

def generar_pdf_orden_compra(orden_id: int, db: Session) -> bytes:
    """Genera el PDF de una orden de compra."""
    
    orden = db.get(OrdenCompra, orden_id)
    if not orden:
        raise RecursoNoEncontradoError("Orden de compra no encontrada")
        
    proveedor = db.get(Proveedor, orden.proveedor_id)
    
    # Convertir imágenes a data URIs
    logo_data_uri = imagen_a_data_uri(Path(LOGO_PDF))
    # Path relativo desde este archivo: ../../../web/static/img/firma_jefe.png
    # Pero mejor usar ruta absoluta o relativa a root del proyecto si es posible, al igual que LOGO_PDF
    # LOGO_PDF usa absolute paths? Appears to be imported.
    # El router usaba: Path(__file__).parent.parent.parent.parent / "web" / "static" / "img" / "firma_jefe.png"
    # Eso es: app/modulos/ordenes_compra/../../../../web -> root/web
    
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    
    # Manejo robusto de firma
    firma_path = base_dir / "web" / "static" / "img" / "firma_jefe.png"
    try:
        firma_data_uri = imagen_a_data_uri(firma_path)
    except Exception:
        firma_data_uri = ""

    # Manejo robusto de logo
    try:
        logo_data_uri = imagen_a_data_uri(Path(LOGO_PDF))
    except Exception:
        logo_data_uri = ""
    
    # Formatear fechas en español
    fecha_emision_es = formatear_fecha_español(orden.fecha_emision) if orden.fecha_emision else "N/A"
    fecha_entrega_es = formatear_fecha_español(orden.fecha_entrega_estimada) if orden.fecha_entrega_estimada else "Por Confirmar"
    
    # Contexto para el template
    context = {
        "orden": orden,
        "proveedor": proveedor,
        "detalles": orden.detalles,
        "logo_path": logo_data_uri,
        "firma_responsable": firma_data_uri,
        "fecha_emision_formateada": fecha_emision_es,
        "fecha_entrega_formateada": fecha_entrega_es,
    }
    
    return GeneradorPDF.generar_pdf("pdf/orden_compra.html", context)
