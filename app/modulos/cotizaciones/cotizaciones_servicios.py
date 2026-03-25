"""
Servicio de Aplicación para Cotizaciones.

Orquesta operaciones que cruzan más de un repositorio o módulo.
Este es el punto de entrada correcto para el próximo módulo que necesite
interactuar con Cotizaciones y Órdenes simultáneamente.

Regla: Los repositorios individuales NO deben instanciarse entre sí.
       Solo este servicio (u otro ServicioAplicacion) puede hacerlo.
"""
from sqlmodel import Session

from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioCotizacion
from app.modulos.ordenes.ordenes_repositorio import RepositorioOrden


class ServicioAplicacionCotizacion:
    """
    Orquestador de lógica de aplicación que cruza Cotizaciones y Órdenes.
    """

    def __init__(self, db: Session):
        self.db = db
        self._repo_cot = RepositorioCotizacion(db)
        self._repo_ordenes = RepositorioOrden(db)

    def obtener_estado_conceptos(self, cotizacion_id: int) -> dict[int, dict]:
        """
        Obtiene el estado de ejecución (OT) para cada concepto de una cotización.
        
        Centraliza la consulta cruzada que antes requería que RepositorioCotizacion
        instanciara RepositorioOrden directamente.

        Returns:
            Dict[concepto_id, {"estado": str, "numero_ot": str, "orden_id": int}]
        """
        conceptos = self._repo_cot.obtener_conceptos(cotizacion_id)
        concepto_ids = [c.id for c in conceptos if c.id is not None]

        if not concepto_ids:
            return {}

        return self._repo_ordenes.obtener_estado_por_conceptos_cotizacion(concepto_ids)

    def obtener_detalle_completo(self, cotizacion_id: int) -> dict:
        """
        Devuelve la cotización con sus conceptos y sus estados de ejecución en OT.
        
        Útil para el próximo módulo que necesite una vista consolidada.
        """
        cotizacion = self._repo_cot.obtener_por_id(cotizacion_id)
        conceptos = self._repo_cot.obtener_conceptos(cotizacion_id)
        estados = self.obtener_estado_conceptos(cotizacion_id)

        return {
            "cotizacion": cotizacion,
            "conceptos": conceptos,
            "estados_ot": estados,
        }
