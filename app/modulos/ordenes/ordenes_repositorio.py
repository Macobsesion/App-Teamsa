from sqlmodel import Session, select
from datetime import date, datetime, timedelta
from typing import Any
from app.base.repositorio import RepositorioCRUD
from app.base.eventos import BusEventos
from app.base.folios import EstrategiaFolioFechaId, GeneradorFolio
from app.base.excepciones import RecursoNoEncontradoError, ReglaNegocioError

from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo, ConceptoOrdenTrabajo
from app.modulos.ordenes.enums import EstadoConceptoOT
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.usuarios.usuarios_modelo import Usuario
from app.modulos.ordenes.eventos import EVENTO_ORDEN_CREADA, EVENTO_ORDEN_FINALIZADA, EVENTO_ORDEN_CANCELADA
from app.nucleo.base_datos import obtener_motor


class RepositorioOrden(RepositorioCRUD[OrdenTrabajo]):
    def __init__(self, db: Session, generador_folio: GeneradorFolio | None = None):
        super().__init__(db)
        self.modelo = OrdenTrabajo
        self.campos_filtrables = {'estado', 'usuario_id'}
        self.generador_folio = generador_folio or EstrategiaFolioFechaId()

    def _pre_procesar_datos_creacion(self, datos: dict[str, Any]) -> dict[str, Any]:
        return datos

    def _post_guardar(self, entidad: OrdenTrabajo, es_nuevo: bool) -> None:
        if es_nuevo:
            BusEventos.publicar(EVENTO_ORDEN_CREADA, {
                "orden_id": entidad.id,
                "cotizacion_id": entidad.cotizacion_id,
                "session_actual": self.db
            })

    def eliminar(self, entidad_id: int) -> None:
        """
        La eliminación física está desactivada para preservar historial.
        """
        raise ReglaNegocioError("La eliminación física está deshabilitada. Por favor, cambie el estado a 'Cancelada'.")

    # ---- Los métodos transaccionales como crear_desde_cotizacion han sido movidos a Capa de Servicios ----

    # ---- Consultas Externas (Inter-módulos) ----
    
    def obtener_estado_por_conceptos_cotizacion(self, concepto_cotizacion_ids: list[int]) -> dict[int, dict]:
        """
        Obtiene el estado de ejecución (OT) para una lista de conceptos de cotización.
        
        Retorna: 
            Dict donde key es concepto_cotizacion_id y value es dict con:
            {"estado": "pendiente"|"completado", "numero_ot": ..., "orden_id": ...}
        """
        estado_conceptos: dict[int, dict] = {}
        if not concepto_cotizacion_ids:
            return estado_conceptos
            
        filas = self.db.exec(
            select(ConceptoOrdenTrabajo, OrdenTrabajo)
            .join(OrdenTrabajo, ConceptoOrdenTrabajo.orden_id == OrdenTrabajo.id)
            .where(ConceptoOrdenTrabajo.concepto_cotizacion_id.in_(concepto_cotizacion_ids))
        ).all()

        for c_ot, ot in filas:
            if c_ot.concepto_cotizacion_id is not None:
                estado_conceptos[c_ot.concepto_cotizacion_id] = {
                    "estado": c_ot.estado,
                    "numero_ot": ot.numero_ot,
                    "orden_id": ot.id,
                }
        return estado_conceptos
