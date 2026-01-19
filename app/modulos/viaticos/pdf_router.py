"""Endpoint para generación de PDF de viáticos."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session

from app.nucleo.base_datos import obtener_sesion_bd
from app.rutas.dependencias import exigir_roles
from app.modulos.viaticos.pdf_generator import generar_pdf_viatico
from app.modulos.usuarios.usuarios_esquemas import UsuarioIdentity

router = APIRouter(prefix="/api/viaticos", tags=["Viáticos - PDF"])


@router.get("/{viatico_id}/pdf")
def descargar_pdf(
    viatico_id: int,
    db: Session = Depends(obtener_sesion_bd),
    _usuario: UsuarioIdentity = Depends(exigir_roles("admin")),
):
    """Genera y descarga el PDF de un viático."""
    try:
        pdf_bytes = generar_pdf_viatico(viatico_id, db)
        
        # Obtener número de viático para el filename
        from app.modulos.viaticos.viaticos_modelo import Viatico
        viatico = db.get(Viatico, viatico_id)
        filename = f"{viatico.numero if viatico else 'viatico'}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")
