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
    def imagen_a_data_uri(ruta_imagen: Path) -> str:
        """Convierte imagen a data URI detectando el tipo MIME automáticamente."""
        import base64
        import mimetypes
        if not ruta_imagen.exists():
            return ""
        try:
            mime_type, _ = mimetypes.guess_type(str(ruta_imagen))
            if not mime_type:
                mime_type = "image/png"
                
            with open(ruta_imagen, 'rb') as f:
                imagen_base64 = base64.b64encode(f.read()).decode('utf-8')
                return f"data:{mime_type};base64,{imagen_base64}"
        except Exception:
            return ""

    @staticmethod
    def generar_pdf(template_name: str, context: Dict[str, Any], base_url: str = f"file://{STATIC_DIR}/") -> bytes:
        """
        Renderiza un template y genera el binario PDF.
        """
        template = templates.env.get_template(template_name)
        html_content = template.render(**context)

        font_config = FontConfiguration()
        
        pdf_bytes = HTML(string=html_content, base_url=base_url).write_pdf(
            stylesheets=[CSS(filename=str(STATIC_DIR / "css" / "pdf.css"))],
            font_config=font_config,
            presentational_hints=True
        )
        
        return pdf_bytes


from abc import ABC, abstractmethod
from sqlmodel import Session
from app.base.constantes import LOGO_PDF, FIRMA_PDF

class GeneradorPDFDocumento(ABC):
    """Template Method para generación de PDFs de documentos."""
    
    plantilla: str  # ej: "pdf/cotizacion.html"
    
    def __init__(self, db: Session):
        self.db = db
    
    def generar(self, entidad_id: int) -> bytes:
        """Template Method: obtener → contexto → PDF."""
        entidad = self._obtener_entidad(entidad_id)
        if not entidad:
            from app.base.excepciones import RecursoNoEncontradoError
            raise RecursoNoEncontradoError(f"Documento {entidad_id} no encontrado")
            
        contexto = self._construir_contexto(entidad)
        contexto.update(self._obtener_assets())
        return GeneradorPDF.generar_pdf(self.plantilla, contexto)
    
    @abstractmethod
    def _obtener_entidad(self, entidad_id: int) -> Any: ...
    
    @abstractmethod
    def _construir_contexto(self, entidad: Any) -> dict: ...
    
    def _obtener_assets(self) -> dict:
        """Carga assets comunes (logo, firma)."""
        return {
            "logo_path": GeneradorPDF.imagen_a_data_uri(Path(LOGO_PDF)),
            "firma_responsable": GeneradorPDF.imagen_a_data_uri(Path(FIRMA_PDF)),
        }
