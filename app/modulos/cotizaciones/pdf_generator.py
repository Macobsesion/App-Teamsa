"""Generador de PDF para cotizaciones usando WeasyPrint."""
from io import BytesIO
from pathlib import Path
from weasyprint import HTML, CSS  # type: ignore
from jinja2 import Template

from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion
from app.modulos.clientes.clientes_modelo import Cliente
from app.base.constantes import FORMATO_FECHA_LARGA, IVA_DESCRIPCION, LOGO_PDF
from sqlmodel import Session  # type: ignore


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
    
    # Convertir logo a base64 para embedder en PDF
    import base64
    logo_path = Path(LOGO_PDF)
    if logo_path.exists():
        with open(logo_path, 'rb') as f:
            logo_base64 = base64.b64encode(f.read()).decode('utf-8')
            logo_data_uri = f"data:image/png;base64,{logo_base64}"
    else:
        logo_data_uri = ""  # Sin logo si no existe
    
    # Convertir firma a base64 si existe
    firma_path = Path(__file__).parent.parent.parent.parent / "web" / "static" / "img" / "firma_jefe.png"
    firma_data_uri = ""
    if firma_path.exists():
        with open(firma_path, 'rb') as f:
            firma_base64 = base64.b64encode(f.read()).decode('utf-8')
            firma_data_uri = f"data:image/png;base64,{firma_base64}"
    
    # Preparar datos para el template
    # Formatear fechas en español
    meses_es = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }
    
    fecha_emision = cotizacion.fecha_emision
    fecha_vigencia = cotizacion.fecha_vigencia
    
    fecha_emision_es = f"{fecha_emision.day} de {meses_es[fecha_emision.month]} de {fecha_emision.year}"
    fecha_vigencia_es = f"{fecha_vigencia.day} de {meses_es[fecha_vigencia.month]} de {fecha_vigencia.year}"
    
    contexto = {
        "cotizacion": cotizacion,
        "cliente": cliente,
        "conceptos": conceptos,
        "logo_path": logo_data_uri,  # Data URI en lugar de ruta de archivo
        "firma_responsable": firma_data_uri,  # Firma del responsable
        "iva_descripcion": IVA_DESCRIPCION,
        "fecha_emision_formateada": fecha_emision_es,
        "fecha_vigencia_formateada": fecha_vigencia_es,
    }
    
    # Renderizar HTML
    html_renderizado = template.render(**contexto)
    
    # Generar PDF
    pdf_bytes = HTML(string=html_renderizado).write_pdf()
    
    return pdf_bytes
