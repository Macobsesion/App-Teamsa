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
        # Detectar intento de manipulación del cotizacion_id
        entidad_bd = self.obtener_por_id(entidad_id)
        viejo_cotizacion = entidad_bd.cotizacion_id
        nuevo_cotizacion = cambios.get("cotizacion_id")
        
        if viejo_cotizacion is not None and nuevo_cotizacion is not None and nuevo_cotizacion != viejo_cotizacion:
            from app.base.excepciones import ReglaNegocioError
            raise ReglaNegocioError("No se puede desvincular o cambiar la cotización madre una vez asignada.")
            
        # Bandera temporal para inyectar si recién se asigna la cotización en Update
        if viejo_cotizacion is None and nuevo_cotizacion:
            self._temp_inyectar_cotizacion = nuevo_cotizacion
            
        return super().actualizar(entidad_id, cambios)

    def _pre_guardar(self, entidad: Viatico, es_nuevo: bool) -> None:
        """Asigna las Ordenes de Trabajo reales si se pasaron ot_ids en el request. Suma totales."""
        if hasattr(self, "_temp_ot_ids"):
            from sqlmodel import select
            from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo
            
            if self._temp_ot_ids:
                ots = self.db.exec(select(OrdenTrabajo).where(OrdenTrabajo.id.in_(self._temp_ot_ids))).all()
                entidad.rutas_ot = list(ots)
            else:
                entidad.rutas_ot = []
            del self._temp_ot_ids
            
        # Calcular auto-suma global
        entidad.total = (
            (entidad.costo_transporte or 0) +
            (entidad.costo_alojamiento or 0) +
            (entidad.costo_alimentos or 0) +
            (entidad.costo_otros or 0)
        )

    def _post_guardar(self, entidad: Viatico, es_nuevo: bool) -> None:
        if es_nuevo:
            from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
            from app.base.folios import EstrategiaFolioHeredado
            from sqlmodel import select

            if entidad.cotizacion_id:
                # 1. Obtener número de cotización madre
                cotizacion = self.db.get(Cotizacion, entidad.cotizacion_id)
                if cotizacion and cotizacion.numero:
                    # 'COT-260307-B' -> '260307B'
                    base_folio = cotizacion.numero.replace("COT-", "").replace("-", "")
                    
                    # 2. Obtener secuencia para esta cotización
                    from sqlalchemy import func
                    conteo = self.db.exec(
                        select(func.count(Viatico.id))
                        .where(Viatico.cotizacion_id == entidad.cotizacion_id)
                    ).first() or 0
                    secuencia = conteo # No sumamos 1 porque el registro ya se guardó (es post_guardar)
                    # Pero espera, si es post_guardar, el registro actual YA está en el conteo.
                    # Si conteo es 1, este es el primero.
                    
                    estrategia = EstrategiaFolioHeredado()
                    entidad.folio = estrategia.generar(PREFIJO_NUMERO_VIATICO, base_folio, secuencia)
                else:
                    # Fallback si no hay número de cotización (no debería pasar)
                    from datetime import date
                    fecha_str = date.today().strftime("%y%m")
                    entidad.folio = f"{PREFIJO_NUMERO_VIATICO}-{fecha_str}-{entidad.id}"
            else:
                # Fallback para viáticos sin cotización
                from datetime import date
                fecha_str = date.today().strftime("%y%m")
                entidad.folio = f"{PREFIJO_NUMERO_VIATICO}-{fecha_str}-{entidad.id}"

            self.db.add(entidad)
            self.db.commit()
            self.db.refresh(entidad)
            
        # Automatización: Inserción de concepto en la Cotización
        inyectar = False
        if es_nuevo and getattr(entidad, "cotizacion_id", None):
            inyectar = True
        elif hasattr(self, "_temp_inyectar_cotizacion") and self._temp_inyectar_cotizacion == entidad.cotizacion_id:
            inyectar = True
            
        if inyectar and not self.skip_injection:
            from app.modulos.cotizaciones.cotizaciones_repositorio import RepositorioConcepto
            repo_concepto = RepositorioConcepto(self.db)
            desc = f"Viáticos: {entidad.proyecto or 'Servicio asignado'} (Ref: {entidad.folio})"
            repo_concepto.crear_concepto(
                cotizacion_id=entidad.cotizacion_id,
                servicio_id=None,
                codigo_sat='78111500', # Transporte de pasajeros
                descripcion=desc,
                unidad='Viaje/Servicio',
                cantidad=1,
                precio_unitario=entidad.total,
                descuento_porcentaje=0
            )
            if hasattr(self, "_temp_inyectar_cotizacion"):
                del self._temp_inyectar_cotizacion
