"""Servicio para generar documentos PDF usando WeasyPrint y Jinja2."""
from typing import Any, Dict
from app.web.jinja import get_templates
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from pathlib import Path
import logging

# WeasyPrint logger setup
logger = logging.getLogger('weasyprint')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.WARNING)

# Configurar templates
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"

templates = get_templates()

class GeneradorPDF:
    """Clase utilitaria para generar PDFs desde templates HTML."""

    @staticmethod
    def generar_pdf(template_name: str, context: Dict[str, Any], base_url: str = f"file://{STATIC_DIR}/") -> bytes:
        """
        Renderiza un template y genera el binario PDF.
        
        Args:
            template_name: Ruta relativa del template en web/templates (ej: 'pdf/orden_compra.html')
            context: Diccionario de variables para Jinja
            base_url: Ruta base para resolver assets estáticos (CSS/Img)

        Returns:
            bytes: Contenido del archivo PDF
        """
        # Renderizar HTML usando Jinja2
        # simulamos un 'request' dummy si es necesario, pero Jinja2Templates.get_template().render() basta
        template = templates.env.get_template(template_name)
        html_content = template.render(**context)

        # Configuración de fuentas y assets
        font_config = FontConfiguration()
        
        # Generar PDF
        # Inyectamos el CSS explícitamente para evitar problemas de resolución de rutas
        pdf_bytes = HTML(string=html_content, base_url=base_url).write_pdf(
            stylesheets=[CSS(filename=str(STATIC_DIR / "css" / "pdf.css"))],
            font_config=font_config,
            # presentational_hints=True para respetar atributos HTML como width/height/align
            presentational_hints=True
        )
        
        return pdf_bytes
