"""Repositorio para órdenes de trabajo."""
from datetime import date, datetime
from decimal import Decimal
from sqlmodel import Session, select
from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo, ConceptoOrdenTrabajo


class RepositorioOrdenTrabajo:
    """Repositorio para gestión de órdenes de trabajo."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generar_siguiente_numero(self) -> str:
        """
        Genera el siguiente número de orden de trabajo.
        Formato: OT-00001, OT-00002, etc.
        """
        statement = select(OrdenTrabajo).order_by(OrdenTrabajo.id.desc()).limit(1)
        ultima = self.db.exec(statement).first()
        
        if not ultima:
            return "OT-00001"
        
        # Extraer número y sumar 1
        try:
            numero_actual = int(ultima.numero.split("-")[1])
            nuevo_numero = numero_actual + 1
            return f"OT-{nuevo_numero:05d}"
        except (IndexError, ValueError):
            return "OT-00001"
    
    def crear_desde_cotizacion(self, cotizacion_id: int, usuario: str, fecha_programada: date | None = None):
        """
        Crea una orden de trabajo desde una cotización.
        
        Copia:
        - Cliente
        - Servicios (solo descripción, cantidad, unidad - SIN precios)
        - Notas públicas (NO las privadas)
        
        NO copia:
        - Precios
        - Descuentos
        - Totales
        - Notas privadas
        """
        from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
        
        # Obtener cotización
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion:
            raise ValueError(f"Cotización {cotizacion_id} no encontrada")
        
        # Generar número
        numero = self.generar_siguiente_numero()
        
        # Crear orden de trabajo
        orden = OrdenTrabajo(
            numero=numero,
            cliente_id=cotizacion.cliente_id,
            cotizacion_id=cotizacion_id,
            estado="pendiente",
            fecha_programada=fecha_programada,
            notas=cotizacion.notas,  # Solo notas públicas
            # NO copiar notas_privadas
            creado_por=usuario,
            modificado_por=usuario,
        )
        
        self.db.add(orden)
        self.db.flush()  # Para obtener el ID
        
        # Copiar conceptos SIN precios
        statement = select(ConceptoCotizacion).where(
            ConceptoCotizacion.cotizacion_id == cotizacion_id
        )
        conceptos = self.db.exec(statement).all()
        
        repo_concepto = RepositorioConceptoOrdenTrabajo(self.db)
        for concepto in conceptos:
            repo_concepto.crear(
                orden_trabajo_id=orden.id,
                servicio_id=concepto.servicio_id,
                descripcion=concepto.descripcion,
                cantidad=concepto.cantidad,
                unidad=concepto.unidad,
                codigo_unidad=concepto.codigo_unidad,
                codigo_sat=concepto.codigo_sat,
                # NO copiar: precio_unitario, descuento_porcentaje
            )
        
        self.db.commit()
        self.db.refresh(orden)
        
        return orden


class RepositorioConceptoOrdenTrabajo:
    """Repositorio para conceptos de órdenes de trabajo."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def crear(
        self,
        orden_trabajo_id: int,
        descripcion: str,
        cantidad: Decimal,
        unidad: str = "Servicio",
        codigo_unidad: str = "E48",
        servicio_id: int | None = None,
        codigo_sat: str | None = None,
    ) -> ConceptoOrdenTrabajo:
        """
        Crea un concepto para una orden de trabajo.
        
        IMPORTANTE: NO incluye precio, descuento ni subtotal.
        """
        concepto = ConceptoOrdenTrabajo(
            orden_trabajo_id=orden_trabajo_id,
            servicio_id=servicio_id,
            descripcion=descripcion,
            cantidad=cantidad,
            unidad=unidad,
            codigo_unidad=codigo_unidad,
            codigo_sat=codigo_sat,
        )
        
        self.db.add(concepto)
        self.db.commit()
        self.db.refresh(concepto)
        
        return concepto
    
    def listar_por_orden(self, orden_trabajo_id: int) -> list[ConceptoOrdenTrabajo]:
        """Obtiene todos los conceptos de una orden de trabajo."""
        statement = select(ConceptoOrdenTrabajo).where(
            ConceptoOrdenTrabajo.orden_trabajo_id == orden_trabajo_id
        )
        return list(self.db.exec(statement).all())
