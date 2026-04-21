
import mimetypes
from pathlib import Path
import base64

def mock_imagen_a_data_uri(ruta_imagen: Path) -> str:
    """Versión mock de la función para probar lógica de mimetypes."""
    if not ruta_imagen.exists():
        return "NOT FOUND"
    try:
        mime_type, _ = mimetypes.guess_type(str(ruta_imagen))
        if not mime_type:
            mime_type = "image/png"
        return f"data:{mime_type};base64,..."
    except Exception as e:
        return str(e)

logo_path = Path("/home/teamsa/htdocs/teamsa.com.mx/teamsa-app-dev/web/static/images/teamsa_logo.webp")
print(f"Testing logo path: {logo_path}")
print(f"Result: {mock_imagen_a_data_uri(logo_path)}")

firma_path = Path("/home/teamsa/htdocs/teamsa.com.mx/teamsa-app-dev/web/static/img/firma_jefe.png")
print(f"Testing firma path: {firma_path}")
print(f"Result: {mock_imagen_a_data_uri(firma_path)}")
