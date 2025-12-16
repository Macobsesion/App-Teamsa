"""Generador de PDF para viáticos usando WeasyPrint."""
from pathlib import Path
from weasyprint import HTML  # type: ignore
from jinja2 import Template

from app.modulos.viaticos.viaticos_modelo import Viatico
from app.modulos.viaticos.viaticos_repositorio import RepositorioViatico
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.base.constantes import FORMATO_FECHA_LARGA, LOGO_PDF
from sqlmodel import Session  # type: ignore


def generar_pdf_viatico(viatico_id: int, db: Session) -> bytes:
    """
    Genera un PDF profesional de un reporte de viáticos.
    
    Args:
        viatico_id: ID del viático
        db: Sesión de base de datos
        
    Returns:
        Bytes del PDF generado
    """
    # Obtener viático y datos relacionados
    viatico = db.get(Viatico, viatico_id)
    if not viatico:
        raise ValueError(f"Viático {viatico_id} no encontrado")
    
    responsable = db.get(Usuario, viatico.responsable_id)
    
    repo = RepositorioViatico(db)
    gastos = repo.obtener_gastos(viatico_id)
    
    # Agrupar gastos por categoría
    gastos_transporte = [g for g in gastos if g.categoria == "transporte"]
    gastos_alojamiento = [g for g in gastos if g.categoria == "alojamiento"]
    gastos_alimentos = [g for g in gastos if g.categoria == "alimentos"]
    gastos_otros = [g for g in gastos if g.categoria == "otros"]
    
    # Leer template HTML
    template_path = Path(__file__).parent.parent.parent.parent / "web" / "templates" / "pdf" / "viatico.html"
    template_content = template_path.read_text(encoding="utf-8")
    template = Template(template_content)
    
    # Preparar datos para el template
    contexto = {
        "viatico": viatico,
        "responsable": responsable,
        "gastos_transporte": gastos_transporte,
        "gastos_alojamiento": gastos_alojamiento,
        "gastos_alimentos": gastos_alimentos,
        "gastos_otros": gastos_otros,
        "logo_path": LOGO_PDF,
        "fecha_inicio_formateada": viatico.fecha_inicio.strftime(FORMATO_FECHA_LARGA),
        "fecha_fin_formateada": viatico.fecha_fin.strftime(FORMATO_FECHA_LARGA),
    }
    
    # Renderizar HTML
    html_renderizado = template.render(**contexto)
    
    # Generar PDF
    pdf_bytes = HTML(string=html_renderizado).write_pdf()
    
    return pdf_bytes
