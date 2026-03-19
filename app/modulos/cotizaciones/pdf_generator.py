"""Generador de PDF para cotizaciones usando WeasyPrint."""
import base64
from io import BytesIO
from pathlib import Path
from app.base.generador_pdf import GeneradorPDF

from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion
from app.modulos.clientes.clientes_modelo import Cliente
from app.base.constantes import FORMATO_FECHA_LARGA, IVA_DESCRIPCION, LOGO_PDF
from app.base.utilidades_fecha import formatear_fecha_español
from sqlmodel import Session  # type: ignore


def imagen_a_data_uri(ruta_imagen: Path) -> str:
    """Convierte imagen a data URI de forma robusta."""
    if not ruta_imagen.exists():
        return ""
    try:
        with open(ruta_imagen, 'rb') as f:
            imagen_base64 = base64.b64encode(f.read()).decode('utf-8')
            return f"data:image/png;base64,{imagen_base64}"
    except Exception:
        return ""


def generar_pdf_cotizacion(cotizacion_id: int, db: Session) -> bytes:
    """
    Genera un PDF profesional de una cotizacion.
    
    Args:
        cotizacion_id: ID de la cotización
        db: Sesión de base de datos
        
    Returns:
        Bytes del PDF generado
    """
    # Obtener cotización y datos relacionados
    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise ValueError(f"Cotización {cotizacion_id} no encontrada")
    
    cliente = db.get(Cliente, cotizacion.cliente_id)
    
    repo = RepositorioCotizacion(db)
    conceptos = repo.obtener_conceptos(cotizacion_id)
    
    # Formatear fechas en español
    logo_data_uri = imagen_a_data_uri(Path(LOGO_PDF))
    firma_path = Path(__file__).parent.parent.parent.parent / "web" / "static" / "img" / "firma_jefe.png"
    firma_data_uri = imagen_a_data_uri(firma_path)
    
    # Formatear fechas en español
    fecha_emision_es = formatear_fecha_español(cotizacion.fecha_emision)
    fecha_vigencia_es = formatear_fecha_español(cotizacion.fecha_vigencia)
    
    contexto = {
        "cotizacion": cotizacion,
        "cliente": cliente,
        "conceptos": conceptos,
        "logo_path": logo_data_uri,
        "firma_responsable": firma_data_uri,
        "iva_descripcion": IVA_DESCRIPCION,
        "fecha_emision_formateada": fecha_emision_es,
        "fecha_vigencia_formateada": fecha_vigencia_es,
    }
    
    # Generar PDF a través del generador central
    return GeneradorPDF.generar_pdf("pdf/cotizacion.html", contexto)
