"""Constantes de la aplicación."""

# Impuestos México
IVA_PORCENTAJE = 0.16
IVA_DESCRIPCION = "IVA 16%"

# Cotizaciones
VIGENCIA_DIAS_DEFAULT = 30
PREFIJO_NUMERO_COTIZACION = "COT"

# Viáticos
PREFIJO_NUMERO_VIATICO = "VIA"

# Formatos de fecha
FORMATO_FECHA_CORTA = "%d/%m/%Y"
FORMATO_FECHA_LARGA = "%d de %B de %Y"
FORMATO_FECHA_HORA = "%d/%m/%Y %H:%M"

# Logotipos
LOGO_WEB = "/static/img/teamsa_logo.webp"  # Para web (navbar, login)
LOGO_PDF = "/teamsa-app/web/static/img/teamsa_logo.png"  # Para PDFs (mejor compatibilidad)

# Catálogos SAT (ejemplos - completar según necesidad)
UNIDADES_MEDIDA_SAT = {
    "H87": "Pieza",
    "E48": "Servicio",
    "HUR": "Hora",
    "MTR": "Metro",
    "KGM": "Kilogramo",
}
