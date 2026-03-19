"""
Procesador central para transformar formularios HTMX multipartes a diccionarios
compatibles con validación Pydantic y gestionar la persistencia inicial de archivos.
"""
from typing import Any
from fastapi import UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.base.archivos_procesador import GestorArchivosPolimorfico

class ProcesadorFormulariosHTMX:
    """Extrae y procesa los campos de un formulario multipart HTTP de HTMX."""

    @staticmethod
    def _es_array_prop(defn: dict) -> bool:
        """Heurística para determinar si un campo fue marcado como array en Pydantic."""
        if defn.get("type") == "array":
            return True
        for key in ("anyOf", "oneOf", "allOf"):
            lst = defn.get(key) or []
            if isinstance(lst, list) and any(
                isinstance(d, dict) and d.get("type") == "array" for d in lst
            ):
                return True
        return "items" in defn

    @staticmethod
    def procesar(
        form: Any,
        props: dict,
        campos: set[str],
        file_fields: dict | None = None,
        entity_id: int | None = None,
        entity_plural: str = "",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Extrae los campos del form-data usando los schemas.
        Returns:
            Tupla (datos_texto, archivos_procesados)
        """
        array_fields = {
            k for k, v in props.items() 
            if isinstance(v, dict) and ProcesadorFormulariosHTMX._es_array_prop(v)
        }
        
        datos: dict[str, Any] = {}
        archivos: dict[str, Any] = {}

        for k in campos:
            if k not in form:
                continue
                
            cfg_archivo = (file_fields or {}).get(k, {})
            is_array = (k in array_fields) or bool(cfg_archivo.get("multiple"))
            
            # Obtener datos crudos
            val_form = form.getlist(k) if (is_array and hasattr(form, "getlist")) else form.get(k)
            
            # Detectar si es un objeto de archivo real
            es_upload = False
            if is_array and isinstance(val_form, list) and len(val_form) > 0 and isinstance(val_form[0], (UploadFile, StarletteUploadFile)):
                es_upload = True
            elif isinstance(val_form, (UploadFile, StarletteUploadFile)):
                es_upload = True
                
            if es_upload:
                # Estrategia de Archivos (Polimorfismo)
                estrategia = GestorArchivosPolimorfico.obtener_estrategia(is_array)
                resultado_archivo = estrategia.guardar_inicial(val_form, entity_id, entity_plural)
                
                if is_array and isinstance(resultado_archivo, str): # Fallback defensivo
                    resultado_archivo = [resultado_archivo]
                    
                if resultado_archivo:
                    archivos[k] = resultado_archivo
                    datos[k] = resultado_archivo
            else:
                datos[k] = val_form

        # Coerción KISS V2: Absolutamente TODOS los strings vacíos
        for k, v in list(datos.items()):
            if isinstance(v, str) and v.strip() == "":
                datos[k] = None

        return datos, archivos
