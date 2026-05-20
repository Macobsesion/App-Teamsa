"""Constantes de la aplicación."""

# Impuestos México
IVA_PORCENTAJE = 0.16
IVA_DESCRIPCION = "IVA 16%"

# Cotizaciones
VIGENCIA_DIAS_DEFAULT = 30
PREFIJO_NUMERO_COTIZACION = "COT"

# Viáticos
PREFIJO_NUMERO_VIATICO = "VIA"

# Órdenes de Compra
PREFIJO_NUMERO_ORDEN_COMPRA = "OC"

# Formatos de fecha
FORMATO_FECHA_CORTA = "%d/%m/%Y"
FORMATO_FECHA_LARGA = "%d de %B de %Y"
FORMATO_FECHA_HORA = "%d/%m/%Y %H:%M"

# Logotipos
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent.parent
LOGO_WEB = "/static/images/teamsa_logo.png"  # Para web (navbar, login) optimizado
LOGO_PDF = str(_ROOT / "web" / "static" / "images" / "teamsa_logo.png")  # Ruta dinámica para el generador PDF
FIRMA_PDF = str(_ROOT / "web" / "static" / "images" / "firma_jefe.png")

# Catálogos SAT (ejemplos - completar según necesidad)
# Unidades SAT
UNIDADES_MEDIDA_SAT = {
    "H87": "Pieza",
    "E48": "Servicio",
    "HUR": "Hora",
    "MTR": "Metro",
    "KGM": "Kilogramo",
}

# Directorios del sistema
STATIC_DIR = _ROOT / "web" / "static"
UPLOADS_DIR = "uploads"  # Ruta relativa al root o absoluta según el entorno

def get_upload_root() -> Path:
    """Retorna la ruta absoluta al directorio de uploads."""
    # En desarrollo/docker suele ser una carpeta en el root del proyecto
    return _ROOT / UPLOADS_DIR
