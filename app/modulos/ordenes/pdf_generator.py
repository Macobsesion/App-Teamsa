"""Generador de PDF para Ordenes de Trabajo."""
from pathlib import Path
from weasyprint import HTML  # type: ignore
from jinja2 import Template
from sqlmodel import Session  # type: ignore

from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.base.constantes import LOGO_PDF
from app.base.utilidades_fecha import formatear_fecha_español
from app.modulos.cotizaciones.pdf_generator import imagen_a_data_uri


def generar_pdf_orden(orden_id: int, db: Session) -> bytes:
    """
    Genera el PDF de una Orden de Trabajo.
    Usa los conceptos SNAPSHOT de la OT (ConceptoOrdenTrabajo),
    no todos los conceptos de la cotización.
    """
    ot = db.get(OrdenTrabajo, orden_id)
    if not ot:
        raise ValueError(f"Orden {orden_id} no encontrada")

    # Cotización de referencia (solo para número y datos de cabecera)
    cotizacion = db.get(Cotizacion, ot.cotizacion_id)

    # ✅ Corrección: usar los conceptos de la OT (subconjunto seleccionado),
    # NO todos los conceptos de la cotización.
    conceptos_ot = ot.conceptos  # lista de ConceptoOrdenTrabajo

    # Template
    template_path = (
        Path(__file__).parent.parent.parent.parent
        / "web" / "templates" / "pdf" / "orden.html"
    )
    if not template_path.exists():
        raise FileNotFoundError(f"Template no encontrado: {template_path}")

    template_content = template_path.read_text(encoding="utf-8")
    template = Template(template_content)

    # Logo (manejo robusto de ruta no encontrada)
    try:
        logo_data_uri = imagen_a_data_uri(Path(LOGO_PDF))
    except Exception:
        logo_data_uri = ""

    contexto = {
        "ot": ot,
        "cotizacion": cotizacion,
        "conceptos": conceptos_ot,  # solo los de esta OT
        "logo_path": logo_data_uri,
        "fecha_programada_fmt": formatear_fecha_español(ot.fecha_programada),
    }

    html_renderizado = template.render(**contexto)
    return HTML(string=html_renderizado).write_pdf()

