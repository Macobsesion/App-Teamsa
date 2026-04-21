"""Generador de PDF para cotizaciones usando WeasyPrint."""
import base64
from io import BytesIO
from pathlib import Path
from app.base.generador_pdf import GeneradorPDF

from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion
from app.modulos.viaticos.viaticos_repositorio import RepositorioViatico
from app.modulos.viaticos.viaticos_modelo import Viatico
from app.modulos.clientes.clientes_modelo import Cliente
from app.base.constantes import FORMATO_FECHA_LARGA, IVA_DESCRIPCION, LOGO_PDF
from app.base.utilidades_fecha import formatear_fecha_español
from sqlmodel import Session  # type: ignore


def imagen_a_data_uri(ruta_imagen: Path) -> str:
    """Convierte imagen a data URI detectando el tipo MIME automáticamente."""
    import mimetypes
    if not ruta_imagen.exists():
        return ""
    try:
        mime_type, _ = mimetypes.guess_type(str(ruta_imagen))
        if not mime_type:
            # Fallback seguro
            mime_type = "image/png"
            
        with open(ruta_imagen, 'rb') as f:
            imagen_base64 = base64.b64encode(f.read()).decode('utf-8')
            return f"data:{mime_type};base64,{imagen_base64}"
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
    # Resolución dinámica de rutas para assets
    from app.base.constantes import _ROOT
    
    logo_data_uri = imagen_a_data_uri(Path(LOGO_PDF))
    firma_path = _ROOT / "web" / "static" / "images" / "firma_jefe.png" # Corregido a 'images' si ahí están los assets
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



def generar_pdf_viatico(viatico_id: int, db: Session) -> bytes:
    """
    Genera un PDF del reporte de viáticos.
    """
    from app.modulos.cotizaciones.viaticos_modelo import Viatico
    from app.modulos.usuarios.usuarios_modelo import Usuario
    from app.modulos.clientes.clientes_modelo import Cliente

    viatico = db.get(Viatico, viatico_id)
    if not viatico:
        raise ValueError(f"Viático {viatico_id} no encontrado")

    responsable = db.get(Usuario, viatico.responsable_id)
    cliente = db.get(Cliente, viatico.cliente_id)

    logo_data_uri = imagen_a_data_uri(Path(LOGO_PDF))

    contexto = {
        "viatico": viatico,
        "responsable": responsable,
        "cliente": cliente.nombre if cliente else "N/A",
        "logo_path": logo_data_uri,
        "fecha_inicio_formateada": formatear_fecha_español(viatico.fecha_creacion),
        "fecha_fin_formateada": formatear_fecha_español(viatico.fecha_creacion), # Simplificación
    }

    return GeneradorPDF.generar_pdf("pdf/viatico.html", contexto)
