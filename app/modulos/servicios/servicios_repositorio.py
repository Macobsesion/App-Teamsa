"""Repositorio para servicios."""
from sqlmodel import Session  # type: ignore

from app.base.repositorio import RepositorioCRUD
from app.modulos.servicios.servicios_modelo import Servicio


class RepositorioServicio(RepositorioCRUD[Servicio]):
    """Repositorio de servicios con búsqueda por clave y descripción."""
    
    modelo = Servicio
    campos_filtrables = {"activo", "tipo"}
    campos_actualizables = {
        "codigo_sat", "codigo_unidad", "clave", "descripcion",
        "tipo", "precio_base", "unidad", "activo", "notas",
        "modificado_por"
    }
    campos_busqueda = {
        "clave": "icontains",
        "descripcion": "icontains"
    }
    orden_por_defecto = ("clave", False)

    def _pre_guardar(self, entidad: Servicio, es_nuevo: bool) -> None:
        """Validar que el servicio no esté en uso activo al inactivar."""
        if not es_nuevo and not entidad.activo:
            from sqlmodel import select
            from app.modulos.cotizaciones.cotizaciones_modelo import ConceptoCotizacion, Cotizacion
            from app.base.excepciones import ReglaNegocioError
            
            # Verificar si existe algún ConceptoCotizacion activo que use este servicio
            uso_activo = self.db.exec(
                select(ConceptoCotizacion)
                .join(Cotizacion, ConceptoCotizacion.cotizacion_id == Cotizacion.id)
                .where(
                    ConceptoCotizacion.servicio_id == entidad.id,
                    Cotizacion.estado.notin_(["cancelada", "rechazada", "finalizada", "modificada"])
                )
            ).first()
            
            if uso_activo:
                raise ReglaNegocioError(f"No se puede inactivar: El servicio está en uso en la cotización activa {uso_activo.cotizacion.numero if uso_activo.cotizacion else uso_activo.cotizacion_id}.")

    def eliminar(self, entidad_id: int) -> None:
        """No permitir eliminar físicamente si tiene uso en cotizaciones."""
        from sqlmodel import select
        from app.modulos.cotizaciones.cotizaciones_modelo import ConceptoCotizacion
        from app.base.excepciones import ReglaNegocioError
        
        # Verificar si existe algún ConceptoCotizacion que use este servicio
        uso = self.db.exec(
            select(ConceptoCotizacion).where(ConceptoCotizacion.servicio_id == entidad_id)
        ).first()
        
        if uso:
            raise ReglaNegocioError("No se puede eliminar el servicio: Está en uso en cotizaciones existentes.")

        return super().eliminar(entidad_id)
