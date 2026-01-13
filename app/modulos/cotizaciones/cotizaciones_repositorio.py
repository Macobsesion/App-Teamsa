"""Repositorio para cotizaciones."""
from datetime import date, timedelta
from decimal import Decimal
from sqlmodel import Session, select  # type: ignore

from app.base.repositorio import RepositorioCRUD
from app.base.constantes import IVA_PORCENTAJE, VIGENCIA_DIAS_DEFAULT, PREFIJO_NUMERO_COTIZACION
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion


class RepositorioCotizacion(RepositorioCRUD[Cotizacion]):
    """Repositorio de cotizaciones con lógica de numeración y cálculos."""
    
    modelo = Cotizacion
    campos_filtrables = {"estado", "cliente_id"}
    campos_actualizables = {
        "cliente_id", "estado", "notas", "notas_privadas", "metodo_pago",
        "descuento_porcentaje", "modificado_por"
    }
    campos_busqueda = {"numero": "icontains"}
    orden_por_defecto = ("numero", True)  # Descendente (más reciente primero)
    
    def generar_siguiente_numero(self) -> str:
        """
        DEPRECATED: Este método ya no se usa para generar números.
        Los números ahora se generan después de insertar en la BD usando el ID.
        
        Se mantiene por compatibilidad pero devuelve una cadena temporal.
        El número real se asigna en generar_numero_desde_id().
        
        Returns:
            String temporal que será reemplazado
        """
        return "TEMP-PENDING"
    
    def generar_numero_desde_id(self, cotizacion_id: int, fecha_emision: date) -> str:
        """
        Genera el número de cotización basado en el ID y la fecha.
        
        Formato: COT-YYMMID
        Ejemplo: COT-26011623 (año 26, mes 01, día 16, ID 23)
        
        Args:
            cotizacion_id: ID de la cotización en la BD
            fecha_emision: Fecha de emisión de la cotización
            
        Returns:
            Número en formato COT-YYMMID
        """
        from app.base.constantes import PREFIJO_NUMERO_COTIZACION
        
        # Formato: COT-YYMMDD + ID
        # Ejemplo: COT-260116 + 23 = COT-26011623
        fecha_str = fecha_emision.strftime("%y%m%d")
        return f"{PREFIJO_NUMERO_COTIZACION}-{fecha_str}{cotizacion_id}"
    
    def eliminar(self, entidad_id: int) -> None:
        """
        Elimina una cotización y todos sus conceptos relacionados.
        
        Args:
            entidad_id: ID de la cotización a eliminar
        """
        # Primero eliminar todos los conceptos asociados
        conceptos = self.obtener_conceptos(entidad_id)
        for concepto in conceptos:
            self.db.delete(concepto)
        
        # Ahora eliminar la cotización
        cotizacion = self.db.get(Cotizacion, entidad_id)
        if not cotizacion:
            raise LookupError("Cotizacion no encontrada")
        
        self.db.delete(cotizacion)
        self.db.commit()
    
    def calcular_fecha_vigencia(self, fecha_emision: date) -> date:
        """
        Calcula la fecha de vigencia basada en la fecha de emisión.
        
        Args:
            fecha_emision: Fecha de emisión de la cotización
            
        Returns:
            Fecha de vigencia (emisión + 30 días por defecto)
        """
        return fecha_emision + timedelta(days=VIGENCIA_DIAS_DEFAULT)
    
    def obtener_conceptos(self, cotizacion_id: int) -> list[ConceptoCotizacion]:
        """Obtiene todos los conceptos de una cotización."""
        return list(self.db.exec(
            select(ConceptoCotizacion)
            .where(ConceptoCotizacion.cotizacion_id == cotizacion_id)
            .order_by(ConceptoCotizacion.id)
        ).all())
    
    def recalcular_totales(self, cotizacion_id: int) -> None:
        """
        Recalcula subtotal, descuento, IVA y total basándose en los conceptos.
        
        Fórmulas (con descuentos a nivel de concepto):
        1. Para cada concepto:
           - subtotal_concepto = cantidad × precio_unitario
           - descuento_concepto = subtotal_concepto × (descuento_porcentaje / 100)
           - importe_concepto = subtotal_concepto - descuento_concepto
        
        2. Para la cotización:
           - subtotal = suma de (cantidad × precio_unitario) de todos los conceptos
           - descuento_global = suma de descuentos de todos los conceptos
           - base_iva = subtotal - descuento_global
           - iva = base_iva × 0.16
           - total = base_iva + iva
        
        Args:
            cotizacion_id: ID de la cotización a recalcular
        """
        conceptos = self.obtener_conceptos(cotizacion_id)
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        
        if not cotizacion:
            return
        
        # Calcular subtotal (sin descuentos) y suma de descuentos
        subtotal = Decimal("0.00")
        descuento_global = Decimal("0.00")
        
        for concepto in conceptos:
            # Subtotal del concepto (sin descuento)
            subtotal_concepto = concepto.cantidad * concepto.precio_unitario
            subtotal += subtotal_concepto
            
            # Calcular descuento del concepto
            if concepto.descuento_porcentaje > 0:
                descuento_concepto = subtotal_concepto * (concepto.descuento_porcentaje / Decimal("100"))
                descuento_global += descuento_concepto
        
        # Base imponible para IVA (subtotal - descuentos)
        base_iva = subtotal - descuento_global
        
        # Calcular IVA sobre la base
        iva = base_iva * Decimal(str(IVA_PORCENTAJE))
        
        # Total final
        total = base_iva + iva
        
        # Actualizar cotización
        cotizacion.subtotal = subtotal
        cotizacion.descuento_global = descuento_global
        cotizacion.iva = iva
        cotizacion.total = total
        
        self.db.add(cotizacion)
        self.db.commit()
        self.db.refresh(cotizacion)


class RepositorioConcepto:
    """Repositorio para conceptos de cotización."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def crear(
        self,
        cotizacion_id: int,
        servicio_id: int | None,
        codigo_sat: str,
        descripcion: str,
        unidad: str,
        cantidad: Decimal,
        precio_unitario: Decimal,
        descuento_porcentaje: Decimal = Decimal("0.00"),
    ) -> ConceptoCotizacion:
        """Crea un concepto y recalcula totales de la cotización.
        
        El importe se calcula como:
        1. subtotal = cantidad × precio_unitario
        2. descuento = subtotal × (descuento_porcentaje / 100)
        3. importe = subtotal - descuento
        """
        # Calcular subtotal del concepto
        subtotal_concepto = cantidad * precio_unitario
        
        # Calcular descuento del concepto
        descuento_monto = subtotal_concepto * (descuento_porcentaje / Decimal("100"))
        
        # Calcular importe final del concepto
        importe = subtotal_concepto - descuento_monto
        
        # Crear concepto
        concepto = ConceptoCotizacion(
            cotizacion_id=cotizacion_id,
            servicio_id=servicio_id,
            codigo_sat=codigo_sat,
            descripcion=descripcion,
            unidad=unidad,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            descuento_porcentaje=descuento_porcentaje,
            importe=importe
        )
        
        self.db.add(concepto)
        self.db.commit()
        self.db.refresh(concepto)
        
        # Recalcular totales de la cotización
        repo_cotizacion = RepositorioCotizacion(self.db)
        repo_cotizacion.recalcular_totales(cotizacion_id)
        
        return concepto
    
    def eliminar(self, concepto_id: int, cotizacion_id: int) -> None:
        """Elimina un concepto y recalcula totales de la cotización."""
        concepto = self.db.get(ConceptoCotizacion, concepto_id)
        if concepto:
            self.db.delete(concepto)
            self.db.commit()
            
            # Recalcular totales
            repo_cotizacion = RepositorioCotizacion(self.db)
            repo_cotizacion.recalcular_totales(cotizacion_id)
