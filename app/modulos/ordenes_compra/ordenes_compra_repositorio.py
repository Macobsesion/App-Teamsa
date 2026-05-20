from datetime import date
from typing import List, Mapping, Any
from sqlmodel import select, func

from app.base.repositorio import RepositorioCRUD
from app.base.mixin_repositorio import MixinFolioMensual
from app.base.folios import GeneradorFolio, EstrategiaFolioMensual
from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra, DetalleOrdenCompra
from app.base.constantes import PREFIJO_NUMERO_ORDEN_COMPRA

class RepositorioOrdenCompra(MixinFolioMensual, RepositorioCRUD[OrdenCompra]):
    prefijo_folio = PREFIJO_NUMERO_ORDEN_COMPRA
    campo_fecha = "fecha_emision"
    modelo = OrdenCompra
    campos_filtrables = {"proveedor_id", "estado", "fecha_emision"}
    campos_actualizables = {
        "proveedor_id", "estado", "fecha_emision", "fecha_entrega_estimada",
        "metodo_pago", "forma_pago", "notas", "notas_privadas", "modificado_por"
    }
    campos_busqueda = {"folio": "icontains", "notas": "icontains"}

    def actualizar(self, entidad_id: int, cambios: Mapping[str, Any]) -> OrdenCompra:
        entidad_bd = self.obtener_por_id(entidad_id)
        
        # Guard de Estado: ¿Es editable?
        from app.base.excepciones import ReglaNegocioError
        if not entidad_bd.es_editable:
            raise ReglaNegocioError(f"La orden de compra {entidad_bd.folio} está en estado '{entidad_bd.estado}' y ya no permite ediciones.")
            
        return super().actualizar(entidad_id, cambios)

    def eliminar(self, entidad_id: int) -> None:
        entidad_bd = self.obtener_por_id(entidad_id)
        
        # Guard de Estado: ¿Es cancelable/eliminable?
        from app.base.excepciones import ReglaNegocioError
        if not entidad_bd.es_cancelable:
            raise ReglaNegocioError(f"La orden de compra {entidad_bd.folio} está en estado '{entidad_bd.estado}' y no puede ser eliminada.")
            
        return super().eliminar(entidad_id)

    def _condiciones_busqueda_personalizada(self, valor_seguro: str) -> list:
        """Permite buscar coincidencias en los conceptos/servicios de la orden de compra."""
        return [
            OrdenCompra.detalles.any(DetalleOrdenCompra.descripcion.ilike(f"%{valor_seguro}%"))
        ]
    
    def _enriquecer_consulta(self, consulta):
        from sqlalchemy.orm import selectinload
        return consulta.options(selectinload(OrdenCompra.detalles))
    
    def _pre_procesar_datos_creacion(self, datos: dict[str, Any]) -> dict[str, Any]:
        """Asigna un folio temporal para evitar violaciones de NOT NULL antes del commit final."""
        import uuid
        datos_procesados = datos.copy()
        if not datos_procesados.get("folio"):
            datos_procesados["folio"] = f"TEMP-{uuid.uuid4().hex[:8]}"
        return datos_procesados

    def generar_numero_desde_id(self, fecha: date | None = None) -> str:
        """Genera el folio con formato OC-YYMMNN."""
        fecha_eval = fecha or date.today()
        return self.generar_folio_mensual(fecha_eval)

    def _post_guardar(self, entidad: OrdenCompra, es_nuevo: bool) -> None:
        """Si es nueva, asigna el folio secuencial mensual."""
        es_temporal = entidad.folio and entidad.folio.startswith("TEMP-")
        if es_nuevo and (not entidad.folio or es_temporal):
            entidad.folio = self.generar_numero_desde_id(entidad.fecha_emision)
            self.db.add(entidad)
            self.db.commit()
            self.db.refresh(entidad)
    
    def obtener_con_detalles(self, id_orden: int) -> OrdenCompra | None:
        """Obtiene una orden cargando ansiosamente sus detalles."""
        # En SQLModel/SQLAlchemy async la carga lazy puede fallar si no se configura bien.
        # Aquí usamos select directo. Si lazy='selectin' en el modelo, el .get() normal funciona.
        # Asumimos configuración correcta, pero si falla, usar .options(selectinload(...))
        return self.obtener_por_id(id_orden)

class RepositorioDetalleOrdenCompra(RepositorioCRUD[DetalleOrdenCompra]):
    modelo = DetalleOrdenCompra
    campos_actualizables = {
        "orden_id", "servicio_id", "descripcion", "cantidad",
        "precio_unitario", "descuento_porcentaje"
    }
