from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from pathlib import Path
import logging

# Configurar logging para WeasyPrint
logger = logging.getLogger('weasyprint')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

BASE_DIR = Path("/teamsa-app")
STATIC_DIR = BASE_DIR / "web" / "static"
css_file = STATIC_DIR / "css" / "pdf.css"

print("Checking CSS file:", css_file)
print("CSS Base URL:", f"file://{STATIC_DIR}/css/")
print("CSS file exists:", css_file.exists())
try:
    with open(css_file, "r") as f:
        print("CSS contents start snippet:", f.read(50))
    css = CSS(filename=str(css_file))
    print("CSS parsed successfully")
except Exception as e:
    print("Error parsing CSS:", e)

html_content = "<html><head><link rel='stylesheet' href='css/pdf.css'></head><body class='info-general'><h1>Hola</h1><div class='titulo-principal'>Prueba de color Teamsa Primary</div></body></html>"
try:
    font_config = FontConfiguration()
    pdf_bytes = HTML(string=html_content, base_url=f"file://{STATIC_DIR}/").write_pdf(
        stylesheets=[CSS(filename=str(css_file))],
        font_config=font_config,
        presentational_hints=True
    )
    print("PDF generated successfully, size:", len(pdf_bytes))
except Exception as e:
    print("Error generating PDF:", e)
