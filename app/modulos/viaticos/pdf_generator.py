"""Generador de PDF para viáticos siguiendo el formato de Responsiva."""
import base64
from pathlib import Path
from typing import Any, Dict
from sqlmodel import Session
from app.base.generador_pdf import GeneradorPDF
from app.modulos.viaticos.viaticos_modelo import Viatico
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.modulos.clientes.clientes_modelo import Cliente
from app.base.constantes import LOGO_PDF
from app.base.utilidades_fecha import formatear_fecha_español

def imagen_a_data_uri(ruta_imagen: Path) -> str:
    """Convierte imagen a data URI detectando el tipo MIME automáticamente."""
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

def generar_pdf_viatico_responsiva(viatico_id: int, db: Session) -> bytes:
    """
    Genera un PDF con el formato de responsiva de entrega de dinero.
    """
    viatico = db.get(Viatico, viatico_id)
    if not viatico:
        raise ValueError(f"Viático {viatico_id} no encontrado")

    responsable = db.get(Usuario, viatico.responsable_id)
    
    logo_data_uri = imagen_a_data_uri(Path(LOGO_PDF))

    # Cálculos adicionales para el desglose de alimentos en el PDF
    # (El modelo almacena el unitario y el total ya calculado en costo_alimentos)
    contexto = {
        "viatico": viatico,
        "responsable": responsable,
        "logo_path": logo_data_uri,
        "fecha_emision_es": formatear_fecha_español(viatico.fecha_emision),
        "fecha_salida_es": formatear_fecha_español(viatico.fecha_salida) if viatico.fecha_salida else "S/F",
        "fecha_regreso_es": formatear_fecha_español(viatico.fecha_regreso) if viatico.fecha_regreso else "S/F",
    }

    return GeneradorPDF.generar_pdf("pdf/viatico_responsiva.html", contexto)
