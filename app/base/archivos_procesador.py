"""
Estrategias polimórficas para el procesamiento de archivos subidos en formularios.
"""
from abc import ABC, abstractmethod
from typing import Any
from fastapi import UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.nucleo.archivos import (
    save_pdf_temp,
    move_pdf_to_entity,
    save_pdf_for_entity,
)

class EstrategiaArchivo(ABC):
    """Interfaz polimórfica para procesar campos de archivos."""
    
    @abstractmethod
    def guardar_inicial(self, val_form: Any, entity_id: int | None, entity_plural: str) -> Any:
        """Guarda el archivo subido de forma temporal o permanente."""
        pass
        
    @abstractmethod
    def confirmar_guardado(self, rutas_temp: Any, entity_id: int, entity_plural: str, cfg: dict) -> Any:
        """Mueve archivos temporales a permanentes."""
        pass
        
    @abstractmethod
    def fusionar_actualizacion(self, rutas_nuevas: Any, rutas_actuales: list, cfg: dict) -> Any:
        """Fusiona archivos nuevos subidos con los que ya existían (para updates)."""
        pass

class ArchivoSimple(EstrategiaArchivo):
    """Estrategia para cargar un único archivo por campo."""
    
    def guardar_inicial(self, val_form: Any, entity_id: int | None, entity_plural: str) -> Any:
        if isinstance(val_form, (UploadFile, StarletteUploadFile)) and (val_form.filename or "").strip():
            if entity_id is not None:
                return save_pdf_for_entity(val_form, entity_plural=entity_plural, entity_id=int(entity_id))
            return save_pdf_temp(val_form)
        return None

    def confirmar_guardado(self, rutas_temp: Any, entity_id: int, entity_plural: str, cfg: dict) -> Any:
        if not rutas_temp:
            return None
        return move_pdf_to_entity(rutas_temp, entity_plural=entity_plural, entity_id=entity_id)
        
    def fusionar_actualizacion(self, rutas_nuevas: Any, rutas_actuales: list, cfg: dict) -> Any:
        # En campos simples, el nuevo archivo sobrescribe al anterior (no hay lista combinada)
        return rutas_nuevas

class ArchivoMultiple(EstrategiaArchivo):
    """Estrategia para cargar múltiples archivos (array) en un solo campo."""
    
    def guardar_inicial(self, val_form: Any, entity_id: int | None, entity_plural: str) -> Any:
        # Si llega un único UploadFile (no una lista), convertirlo a lista
        if isinstance(val_form, (UploadFile, StarletteUploadFile)):
            val_form = [val_form]
            
        rutas: list[str] = []
        if isinstance(val_form, list):
            for f in val_form:
                if isinstance(f, (UploadFile, StarletteUploadFile)) and (f.filename or "").strip():
                    if entity_id is not None:
                        rutas.append(save_pdf_for_entity(f, entity_plural=entity_plural, entity_id=int(entity_id)))
                    else:
                        rutas.append(save_pdf_temp(f))
        return rutas if rutas else None

    def confirmar_guardado(self, rutas_temp: Any, entity_id: int, entity_plural: str, cfg: dict) -> Any:
        if not rutas_temp:
            return []
            
        if not isinstance(rutas_temp, list):
            rutas_temp = [rutas_temp]
            
        finales = [move_pdf_to_entity(t, entity_plural=entity_plural, entity_id=entity_id) for t in rutas_temp]
        
        # Validar max archivos
        if cfg.get("max") and len(finales) > int(cfg["max"]):
            raise ValueError(f"Máximo {int(cfg['max'])} archivos")
            
        return finales

    def fusionar_actualizacion(self, rutas_nuevas: Any, rutas_actuales: list, cfg: dict) -> Any:
        if not rutas_nuevas:
            rutas_nuevas = []
        elif not isinstance(rutas_nuevas, list):
            rutas_nuevas = [rutas_nuevas]
            
        combinado = rutas_actuales + rutas_nuevas
        if cfg.get("max") and len(combinado) > int(cfg["max"]):
            raise ValueError(f"Máximo {int(cfg['max'])} archivos")
            
        return combinado

class GestorArchivosPolimorfico:
    """Fábrica y despachador (Strategy Context)."""
    
    @staticmethod
    def obtener_estrategia(is_array_or_multiple: bool) -> EstrategiaArchivo:
        return ArchivoMultiple() if is_array_or_multiple else ArchivoSimple()
