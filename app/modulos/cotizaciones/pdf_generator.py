"""Generador de PDF para cotizaciones usando WeasyPrint."""
import base64
from io import BytesIO
from pathlib import Path
from weasyprint import HTML, CSS  # type: ignore
from jinja2 import Template

from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion
from app.modulos.clientes.clientes_modelo import Cliente
from app.base.constantes import FORMATO_FECHA_LARGA, IVA_DESCRIPCION, LOGO_PDF
from app.base.utilidades_fecha import formatear_fecha_español
from sqlmodel import Session  # type: ignore


def imagen_a_data_uri(ruta_imagen: Path) -> str:
    """
    Convierte una imagen a data URI base64 para embedding en PDF.
    
    Args:
        ruta_imagen: Ruta a la imagen
        
    Returns:
        Data URI en formato data:image/png;base64,{contenido} o string vacío si no existe
    """
    if not ruta_imagen.exists():
        return ""
    
    with open(ruta_imagen, 'rb') as f:
        imagen_base64 = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/png;base64,{imagen_base64}"


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
    
    # Leer template HTML
    template_path = Path(__file__).parent.parent.parent.parent / "web" / "templates" / "pdf" / "cotizacion.html"
    template_content = template_path.read_text(encoding="utf-8")
    template = Template(template_content)
    
    # Convertir imágenes a data URIs
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
    
    # Renderizar HTML
    html_renderizado = template.render(**contexto)
    
    # Generar PDF
    pdf_bytes = HTML(string=html_renderizado).write_pdf()
    
    return pdf_bytes
