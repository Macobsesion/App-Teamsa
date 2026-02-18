"""Generador de PDF para Ordenes de Trabajo."""
import base64
from pathlib import Path
from weasyprint import HTML  # type: ignore
from jinja2 import Template
from sqlmodel import Session  # type: ignore

from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion
from app.base.constantes import LOGO_PDF
from app.base.utilidades_fecha import formatear_fecha_español

from app.modulos.cotizaciones.pdf_generator import imagen_a_data_uri

def generar_pdf_orden(orden_id: int, db: Session) -> bytes:
    """
    Genera el PDF de una Orden de Trabajo.
    """
    ot = db.get(OrdenTrabajo, orden_id)
    if not ot:
        raise ValueError(f"Orden {orden_id} no encontrada")
    
    # Obtener cotizacion relacionada para referencia
    cotizacion = db.get(Cotizacion, ot.cotizacion_id)
    
    # Obtener conceptos (trabajos a realizar) de la cotización
    repo_cot = RepositorioCotizacion(db)
    conceptos = repo_cot.obtener_conceptos(ot.cotizacion_id)
    
    # Template
    template_path = Path(__file__).parent.parent.parent.parent / "web" / "templates" / "pdf" / "orden.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Template no encontrado: {template_path}")
        
    template_content = template_path.read_text(encoding="utf-8")
    template = Template(template_content)
    
    # Recursos
    # Recursos (Manejo robusto)
    try:
        logo_data_uri = imagen_a_data_uri(Path(LOGO_PDF))
    except Exception:
        logo_data_uri = ""
    
    # Contexto
    contexto = {
        "ot": ot,
        "cotizacion": cotizacion,
        "conceptos": conceptos,
        "logo_path": logo_data_uri,
        "fecha_programada_fmt": formatear_fecha_español(ot.fecha_programada)
    }
    
    html_renderizado = template.render(**contexto)
    
    pdf_bytes = HTML(string=html_renderizado).write_pdf()
    return pdf_bytes
