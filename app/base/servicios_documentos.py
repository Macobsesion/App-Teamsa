from typing import Generic, TypeVar, Optional, List, Dict, Any
from sqlmodel import Session, select
from datetime import date
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.base.documentos_modelo import BaseDocumento
from app.base.base_detalle import BaseDetalleTransaccional
from app.base.constantes import IVA_PORCENTAJE

TDocumento = TypeVar("TDocumento", bound=BaseDocumento)
TDetalle = TypeVar("TDetalle", bound=BaseDetalleTransaccional)

class ServicioDocumentoFinanciero(Generic[TDocumento, TDetalle], ABC):
    """
    Servicio base abstracto para gestionar el ciclo de vida de documentos financieros
    (Cotizaciones, Ordenes de Compra) usando el patrón Template Method.
    Depende de la abstracción de un Repositorio, no directamente de la base de datos.
    """
    
    def __init__(self, repo_documento: Any):
        self.repo_documento = repo_documento
        # Aislamos la db en caso de necesitar flush directos por SQLAlchemy
        self.db = getattr(repo_documento, "db", None)
        if not self.db:
            raise ValueError("El repositorio inyectado debe proveer acceso a la sesión (db)")

    def crear_documento(self, datos_cabecera: Dict[str, Any], items: List[Dict[str, Any]]) -> TDocumento:
        """
        Template Method que orquesta la creación de un documento.
        Pasos:
        1. Validar datos
        2. Crear instancia (cabecera)
        3. Generar folio
        4. Procesar detalles (items)
        5. Calcular totales
        6. Guardar y Auditar
        """
        self._validar_datos(datos_cabecera, items)
        
        # Crear instancia base
        documento = self._crear_instancia_cabecera(datos_cabecera)
        
        # Asignar folio temporal para permitir flush
        documento.folio = f"TEMP-{uuid.uuid4()}"
        
        # Guardar preliminarmente para tener ID
        self.db.add(documento)
        self.db.flush()
        
        # Generar folio real (ahora que tenemos ID)
        folio_real = self._generar_folio_final(documento)
        if folio_real:
            documento.folio = folio_real
        
        # Procesar items
        items_orm = self._procesar_detalles(documento, items)
        if items_orm:
            self.db.add_all(items_orm)
            self.db.flush()
            self.db.refresh(documento)
        
        # Calcular totales (subtotal, iva, total) usando los objetos instanciados para saltar el lazy load ORM cache
        self._calcular_totales_cabecera(documento, items_orm)
        
        # Guardado final DELEGADO AL REPOSITORIO
        # En lugar de hacer commit manual, usamos el repo para asegurar auditoría y Domain Events
        documento_guardado = self.repo_documento.guardar(documento)
        
        return documento_guardado

    @abstractmethod
    def _crear_instancia_cabecera(self, datos: Dict[str, Any]) -> TDocumento:
        """Crea la instancia del modelo de cabecera a partir de los datos."""
        pass

    @abstractmethod
    def _procesar_detalles(self, documento: TDocumento, items: List[Dict[str, Any]]) -> None:
        """Crea y asocia los detalles (items) al documento."""
        pass
    
    def _validar_datos(self, datos: Dict[str, Any], items: List[Dict[str, Any]]) -> None:
        """Validaciones comunes. Puede ser sobreescrito."""
        if not items:
            raise ValueError("El documento debe tener al menos un concepto/item.")

    def _generar_folio_final(self, documento: TDocumento) -> str | None:
        """Genera un folio final usando el ID del documento."""
        return None

    def _calcular_totales_cabecera(self, documento: TDocumento, items_orm: Optional[List[TDetalle]] = None) -> None:
        """
        Suma los importes de los detalles y calcula impuestos.
        """
        # Usar los items creados explicitos o intenta obtener la relación de detalles dinámicamente
        if items_orm is not None:
            detalles = items_orm
        else:
            detalles = getattr(documento, 'detalles', getattr(documento, 'conceptos', []))
        
        subtotal = sum(d.importe for d in detalles)
        iva = self._calcular_impuestos(documento, subtotal)
        total = subtotal + iva
        
        documento.subtotal = subtotal
        documento.iva = iva
        documento.total = total

    def _calcular_impuestos(self, documento: TDocumento, subtotal: Decimal) -> Decimal:
        """Calcula el IVA/Impuestos usando la tasa configurada en constantes."""
        return subtotal * Decimal(str(IVA_PORCENTAJE))
