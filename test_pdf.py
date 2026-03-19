from weasyprint import HTML, CSS
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"
css_file = STATIC_DIR / "css" / "pdf.css"

print("Checking CSS path:", css_file)
print("CSS file exists:", css_file.exists())
try:
    css = CSS(filename=str(css_file))
    print("CSS loaded successfully")
except Exception as e:
    print("Error loading CSS:", e)

html_content = "<html><head><link rel='stylesheet' href='css/pdf.css'></head><body><h1>Hola</h1></body></html>"
try:
    pdf_bytes = HTML(string=html_content, base_url=f"file://{STATIC_DIR}/").write_pdf(
        stylesheets=[CSS(filename=str(css_file))],
        presentational_hints=True
    )
    print("PDF generated successfully, size:", len(pdf_bytes))
except Exception as e:
    print("Error generating PDF:", e)
