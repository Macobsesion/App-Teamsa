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
        """
        Calcula la siguiente secuencia del mes obteniendo el folio con el valor más alto.
        Esto evita colisiones si se han eliminado registros anteriormente.
        """
        primer_dia = fecha.replace(day=1)
        if primer_dia.month == 12:
            sig_mes = primer_dia.replace(year=primer_dia.year + 1, month=1)
        else:
            sig_mes = primer_dia.replace(month=primer_dia.month + 1)
        
        # Condiciones de fecha
        col_fecha = getattr(self.modelo, self.campo_fecha)
        condiciones = [col_fecha >= primer_dia, col_fecha < sig_mes]
        
        # Hook para filtros adicionales (ej: excluir versiones de cotización)
        if self.filtro_secuencia_extra:
            condiciones.extend(self.filtro_secuencia_extra())
            
        col_folio = getattr(self.modelo, self.campo_folio)
        # Excluir folios provisionales (deben empezar con el prefijo)
        condiciones.append(col_folio.like(f"{self.prefijo_folio}-%"))
        
        # Consultar el folio más alto del mes
        ultimo_registro = self.db.exec(
            select(self.modelo)
            .where(and_(*condiciones))
            .order_by(col_folio.desc())
        ).first()
        
        if ultimo_registro:
            valor_folio = getattr(ultimo_registro, self.campo_folio)
            try:
                if "-" in valor_folio:
                    partes = valor_folio.split("-")
                    # La segunda parte contiene YYMM y la secuencia (ej: 260508)
                    bloque = partes[1]
                    # La fecha tiene 4 dígitos (YYMM), el resto es la secuencia
                    sec_str = bloque[4:]
                    if sec_str.isdigit():
                        return int(sec_str) + 1
            except Exception:
                pass
                
        # Fallback si no hay registros o falla el parseo
        condiciones_conteo = [col_fecha >= primer_dia, col_fecha < sig_mes]
        if self.filtro_secuencia_extra:
            condiciones_conteo.extend(self.filtro_secuencia_extra())
        conteo = self.db.exec(
            select(func.count(self.modelo.id)).where(and_(*condiciones_conteo))
        ).first() or 0
        return conteo + 1
    
    def generar_folio_mensual(self, fecha: date) -> str:
        """Genera el folio final usando la estrategia mensual."""
        from app.base.folios import EstrategiaFolioMensual
        secuencia = self._obtener_siguiente_secuencia_mensual(fecha)
        return EstrategiaFolioMensual().generar(self.prefijo_folio, fecha, secuencia)
