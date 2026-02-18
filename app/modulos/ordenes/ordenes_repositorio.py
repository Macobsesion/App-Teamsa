from sqlmodel import Session, select
from datetime import date
from typing import Any
from app.base.repositorio import RepositorioCRUD
from app.base.eventos import BusEventos
from app.base.folios import EstrategiaFolioFechaId, GeneradorFolio

from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
from app.modulos.ordenes.eventos import EVENTO_ORDEN_CREADA
from app.nucleo.base_datos import obtener_motor
from app.base.excepciones import RecursoNoEncontradoError

class RepositorioOrden(RepositorioCRUD[OrdenTrabajo]):
    def __init__(self, db: Session, generador_folio: GeneradorFolio | None = None):
        super().__init__(db)
        self.modelo = OrdenTrabajo
        self.campos_filtrables = {'estado', 'usuario_id'}
        # Inyección de dependencia (si no se provee, usar default)
        self.generador_folio = generador_folio or EstrategiaFolioFechaId()
    
    def _pre_procesar_datos_creacion(self, datos: dict[str, Any]) -> dict[str, Any]:
        """
        Hook validación básica.
        Nota: La generación de número y snapshot ahora se maneja en el Factory Method del modelo.
        """
        return datos

    def _post_guardar(self, entidad: OrdenTrabajo, es_nuevo: bool) -> None:
        """
        Publica eventos de dominio después de guardar.
        Ya NO actualiza directamente la cotización (desacoplamiento).
        """
        if es_nuevo:
            BusEventos.publicar(EVENTO_ORDEN_CREADA, {
                "orden_id": entidad.id,
                "cotizacion_id": entidad.cotizacion_id,
                "session_factory": lambda: Session(obtener_motor()) # Pasar factory para que el handler cree su sesión
            })

    def crear_desde_cotizacion(self, cotizacion_id: int, fecha_programada: date, hora_programada: str, duracion: int, usuario: str) -> OrdenTrabajo:
        """
        Orquesta la creación de una Orden a partir de una Cotización.
        """
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion:
            raise RecursoNoEncontradoError(f"Cotización {cotizacion_id} no encontrada")

        # Usar Factory Method para crear instancia con reglas de negocio (Snapshot)
        # Usamos la estrategia inyectada en el repositorio
        orden = OrdenTrabajo.crear_desde_cotizacion(
            cotizacion=cotizacion,
            fecha_programada=fecha_programada,
            hora_programada=hora_programada,
            duracion=duracion,
            usuario_id=usuario,
            generador_folio=self.generador_folio
        )
        
        # Guardar usando métodos internos
        self.db.add(orden)
        self.db.commit()
        self.db.refresh(orden)
        
        # Hook para actualizar estado cotización (se mantiene aquí por ahora)
        self._post_guardar(orden, es_nuevo=True)
        
        return orden
        

