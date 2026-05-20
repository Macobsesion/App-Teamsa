from datetime import date
from typing import Callable, Any
from sqlmodel import select, and_, func

class MixinFolioMensual:
    """Composición: agrega capacidad de folio mensual a cualquier repositorio."""
    
    # Subclases deben definir (o usar defaults):
    prefijo_folio: str = ""
    campo_folio: str = "folio"           # nombre del campo en el modelo
    campo_fecha: str = "fecha_emision"   # campo de fecha para la secuencia
    filtro_secuencia_extra: Callable | None = None  # filtros extra (ej: excluir versiones)
    
    def _obtener_siguiente_secuencia_mensual(self, fecha: date) -> int:
        """Calcula siguiente secuencia del mes (REUTILIZABLE)."""
        primer_dia = fecha.replace(day=1)
        if primer_dia.month == 12:
            sig_mes = primer_dia.replace(year=primer_dia.year + 1, month=1)
        else:
            sig_mes = primer_dia.replace(month=primer_dia.month + 1)
        
        # Acceso dinámico al modelo y sus campos
        col_fecha = getattr(self.modelo, self.campo_fecha)
        condiciones = [col_fecha >= primer_dia, col_fecha < sig_mes]
        
        # Hook para filtros adicionales (ej: excluir versiones de cotización)
        if self.filtro_secuencia_extra:
            # Si es un método de instancia, lo llamamos con self
            condiciones.extend(self.filtro_secuencia_extra())
        
        conteo = self.db.exec(
            select(func.count(self.modelo.id)).where(and_(*condiciones))
        ).first() or 0
        return conteo + 1
    
    def generar_folio_mensual(self, fecha: date) -> str:
        """Genera el folio final usando la estrategia mensual."""
        from app.base.folios import EstrategiaFolioMensual
        secuencia = self._obtener_siguiente_secuencia_mensual(fecha)
        return EstrategiaFolioMensual().generar(self.prefijo_folio, fecha, secuencia)
