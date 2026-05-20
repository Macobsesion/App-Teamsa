from app.base.generador_pdf import GeneradorPDF, GeneradorPDFDocumento
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.viaticos.viaticos_modelo import Viatico
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.modulos.clientes.clientes_modelo import Cliente
from app.base.constantes import IVA_DESCRIPCION
from app.base.utilidades_fecha import formatear_fecha_español
from sqlmodel import Session


class GeneradorPDFCotizacion(GeneradorPDFDocumento):
    """Generador especializado para Cotizaciones."""
    plantilla = "pdf/cotizacion.html"

    def _obtener_entidad(self, entidad_id: int) -> Cotizacion:
        return self.db.get(Cotizacion, entidad_id)

    def _construir_contexto(self, entidad: Cotizacion) -> dict:
        from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion
        
        cliente = self.db.get(Cliente, entidad.cliente_id)
        repo = RepositorioCotizacion(self.db)
        conceptos = repo.obtener_conceptos(entidad.id)

        return {
            "cotizacion": entidad,
            "cliente": cliente,
            "conceptos": conceptos,
            "iva_descripcion": IVA_DESCRIPCION,
            "fecha_emision_formateada": formatear_fecha_español(entidad.fecha_emision),
            "fecha_vigencia_formateada": formatear_fecha_español(entidad.fecha_vigencia),
        }


class GeneradorPDFViatico(GeneradorPDFDocumento):
    """Generador especializado para Viáticos."""
    plantilla = "pdf/viatico.html"

    def _obtener_entidad(self, entidad_id: int) -> Viatico:
        return self.db.get(Viatico, entidad_id)

    def _construir_contexto(self, entidad: Viatico) -> dict:
        responsable = self.db.get(Usuario, entidad.responsable_id)
        cliente = self.db.get(Cliente, entidad.cliente_id)

        return {
            "viatico": entidad,
            "responsable": responsable,
            "cliente": cliente.nombre if cliente else "N/A",
            "fecha_inicio_formateada": formatear_fecha_español(entidad.fecha_creacion),
            "fecha_fin_formateada": formatear_fecha_español(entidad.fecha_creacion),  # Simplificación
        }


def generar_pdf_cotizacion(cotizacion_id: int, db: Session) -> bytes:
    """Genera un PDF profesional de una cotización."""
    return GeneradorPDFCotizacion(db).generar(cotizacion_id)


def generar_pdf_viatico(viatico_id: int, db: Session) -> bytes:
    """Genera un PDF del reporte de viáticos."""
    return GeneradorPDFViatico(db).generar(viatico_id)
