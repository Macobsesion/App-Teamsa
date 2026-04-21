
import sys
import os
from pathlib import Path

# Añadir el path del proyecto
sys.path.append("/home/teamsa/htdocs/teamsa.com.mx/teamsa-app-dev")

from app.base.constantes import LOGO_PDF, _ROOT
from app.modulos.cotizaciones.pdf_generator import imagen_a_data_uri

def verify_logo():
    print(f"Project ROOT: {_ROOT}")
    print(f"LOGO_PDF path: {LOGO_PDF}")
    
    path = Path(LOGO_PDF)
    if path.exists():
        print(f"✓ Logo exists at: {path}")
    else:
        print(f"✗ Logo NOT FOUND at: {path}")
        return
        
    data_uri = imagen_a_data_uri(path)
    if data_uri.startswith("data:image/webp;base64,"):
        print("✓ Data URI generated with correct MIME type (image/webp).")
    elif data_uri == "":
        print("✗ Data URI generation FAILED.")
    else:
        print(f"✗ Data URI has unexpected MIME type: {data_uri[:30]}...")

def verify_firma():
    firma_path = _ROOT / "web" / "static" / "img" / "firma_jefe.png"
    if firma_path.exists():
        print(f"✓ Firma exists at: {firma_path}")
    else:
        print(f"✗ Firma NOT FOUND at: {firma_path}")

if __name__ == "__main__":
    verify_logo()
    verify_firma()
