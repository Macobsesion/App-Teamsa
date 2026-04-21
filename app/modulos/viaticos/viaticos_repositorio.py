"""Repositorio CRUD para Viáticos."""
from typing import Any
from sqlmodel import Session

from app.base.repositorio import RepositorioCRUD
from app.modulos.viaticos.viaticos_modelo import Viatico
from app.base.constantes import PREFIJO_NUMERO_VIATICO

class RepositorioViatico(RepositorioCRUD[Viatico]):
    modelo = Viatico
    campos_filtrables = {"estado", "cliente_id", "responsable_id"}
    campos_busqueda = {"folio": "icontains", "proyecto": "icontains"}
    orden_por_defecto = ("id", True)
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.skip_injection = False # Por defecto inyecta concepto

    def _enriquecer_consulta(self, consulta):
        """Asegura carga inmediata de relaciones críticas para evitar lazy loading en UI."""
        from sqlalchemy.orm import selectinload
        return consulta.options(
            selectinload(Viatico.rutas_ot),
            selectinload(Viatico.responsable),
            selectinload(Viatico.cliente)
        )

    def _pre_procesar_datos_creacion(self, datos: dict[str, Any]) -> dict[str, Any]:
        import uuid
        datos_procesados = dict(datos)
        if not datos_procesados.get("folio"):
            datos_procesados["folio"] = "TEMP-" + str(uuid.uuid4())[:8]
        self._temp_ot_ids = datos_procesados.pop("ot_ids", [])
        return datos_procesados

    def _pre_procesar_cambios(self, cambios: dict[str, Any]) -> dict[str, Any]:
        cambios_procesados = dict(cambios)
        if "ot_ids" in cambios_procesados:
            self._temp_ot_ids = cambios_procesados.pop("ot_ids")
        return cambios_procesados

    def actualizar(self, entidad_id: int, cambios: dict[str, Any]) -> Viatico:
        entidad_bd = self.obtener_por_id(entidad_id)
        
        # Guard de Estado: ¿Es editable?
        from app.base.excepciones import ReglaNegocioError
        from app.modulos.viaticos.enums import EstadoViatico
        
        # Permitir la transición a 'cancelado' o 'finalizado' independientemente de si es editable para otros campos
        from app.modulos.viaticos.enums import EstadoViatico
        estados_finales = [EstadoViatico.CANCELADO.value, EstadoViatico.FINALIZADO.value]
        es_cambio_estado = cambios.get("estado") in estados_finales
        
        if not entidad_bd.es_editable and not es_cambio_estado:
            raise ReglaNegocioError(f"El viático {entidad_bd.folio} está en estado '{entidad_bd.estado}' y ya no permite ediciones.")

        # Detectar intento de manipulación del cotizacion_id
        viejo_cotizacion = entidad_bd.cotizacion_id
        nuevo_cotizacion = cambios.get("cotizacion_id")
        
        if viejo_cotizacion is not None and nuevo_cotizacion is not None and nuevo_cotizacion != viejo_cotizacion:
            raise ReglaNegocioError("No se puede desvincular o cambiar la cotización madre una vez asignada.")
            
        return super().actualizar(entidad_id, cambios)

    def eliminar(self, entidad_id: int) -> None:
        entidad_bd = self.obtener_por_id(entidad_id)
        
        # Guard de Estado: ¿Es cancelable/eliminable?
        from app.base.excepciones import ReglaNegocioError
        if not entidad_bd.es_cancelable:
            raise ReglaNegocioError(f"El viático {entidad_bd.folio} está en estado '{entidad_bd.estado}' y no puede ser eliminado.")
            
        return super().eliminar(entidad_id)

    def _pre_guardar(self, entidad: Viatico, es_nuevo: bool) -> None:
        """Asocia Ordenes de Trabajo, gestiona el estado PROGRAMADO y captura snapshots."""
        # Captura de Snapshots vía Servicio (Regla 4 y 5)
        # Importación local para evitar importación circular
        from app.modulos.viaticos.viaticos_servicios import ServicioViaticos
        ServicioViaticos.capturar_snapshots_estaticos(self.db, entidad)

        if hasattr(self, "_temp_ot_ids"):
            from sqlmodel import select
            from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
            
            if self._temp_ot_ids:
                ots = self.db.exec(select(OrdenTrabajo).where(OrdenTrabajo.id.in_(self._temp_ot_ids))).all()
                entidad.rutas_ot = list(ots)
            else:
                entidad.rutas_ot = []
            del self._temp_ot_ids

    def _post_guardar(self, entidad: Viatico, es_nuevo: bool) -> None:
        """Generación de Folio definitivo tras la creación."""
        if es_nuevo:
            from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
            from app.base.folios import EstrategiaFolioHeredado
            from sqlmodel import select
            from sqlalchemy import func

            if entidad.cotizacion_id:
                cotizacion = self.db.get(Cotizacion, entidad.cotizacion_id)
                if cotizacion and cotizacion.numero:
                    # Extraer base limpia (ej: COT-260201 -> 260201)
                    base_folio = cotizacion.numero.replace("COT-", "").replace("-", "")
                    
                    # Contar viáticos previos para esta cotización
                    conteo = self.db.exec(
                        select(func.count(Viatico.id))
                        .where(Viatico.cotizacion_id == entidad.cotizacion_id)
                        .where(Viatico.id < entidad.id)
                    ).first() or 0
                    
                    # Generar folio idéntico al patrón de OT: VIA-BASE-SEC
                    entidad.folio = f"VIA-{base_folio}-{conteo + 1}"
                else:
                    entidad.folio = f"VIA-{entidad.id:04d}"
            else:
                entidad.folio = f"VIA-S-{entidad.id:04d}"

            self.db.add(entidad)
            self.db.flush()
