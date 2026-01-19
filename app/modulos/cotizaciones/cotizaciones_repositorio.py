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
    
    def listar(self, filtros: dict | None = None) -> list[Cotizacion]:
        """Lista cotizaciones incluyendo datos del cliente (Eager Loading)."""
        from sqlmodel import select
        from sqlalchemy.orm import selectinload
        
        # Iniciar query base
        statement = select(self.modelo)
        
        # Aplicar filtros (logica copiada/reusada de RepositorioCRUD o simple)
        if filtros:
            for campo, valor in filtros.items():
                if hasattr(self.modelo, campo):
                    statement = statement.where(getattr(self.modelo, campo) == valor)
        
        # Ordenamiento default
        col_orden = getattr(self.modelo, self.orden_por_defecto[0])
        if self.orden_por_defecto[1]:
            statement = statement.order_by(col_orden.desc())
        else:
            statement = statement.order_by(col_orden.asc())
            
        # Eager loading CLAVE
        statement = statement.options(selectinload(Cotizacion.cliente))
        
        return list(self.db.exec(statement).all())

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
        
        # Delegar lógica de cálculo al servicio de dominio
        from app.modulos.cotizaciones.servicios import ServicioCalculadoraCotizacion
        
        totales = ServicioCalculadoraCotizacion.calcular_totales(conceptos)
        
        # Actualizar cotización con resultados del servicio
        cotizacion.subtotal = totales["subtotal"]
        cotizacion.descuento_global = totales["descuento_global"]
        cotizacion.iva = totales["iva"]
        cotizacion.total = totales["total"]
        
        self.db.add(cotizacion)
        self.db.commit()
        self.db.refresh(cotizacion)

    def obtener_versiones_familia(self, id_cotizacion_madre: int) -> list[tuple[int, str]]:
        """
        Obtiene todas las versiones de una familia de cotizaciones.
        
        Args:
            id_cotizacion_madre: ID de la cotización madre (original)
        
        Returns:
            Lista de tuplas (id, version_letra) ordenadas
        """
        from sqlmodel import or_
        
        statement = select(Cotizacion).where(
            or_(
                Cotizacion.id == id_cotizacion_madre,
                Cotizacion.cotizacion_original_id == id_cotizacion_madre
            )
        )
        results = self.db.exec(statement).all()
        
        return [(c.id, c.version_letra) for c in results]

    def crear_completa(self, data: dict, usuario_id: str) -> Cotizacion:
        """
        Crea una cotización completa con conceptos en una sola transacción.
        Encapsula toda la lógica de negocio de creación.
        """
        from datetime import date
        from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
        from app.modulos.clientes.clientes_repositorio import RepositorioCliente
        
        fecha_hoy = date.today()
        
        # 1. Crear cotización base
        cotizacion = Cotizacion(
            numero="TEMP",
            numero_version="TEMP",
            cliente_id=data['cliente_id'],
            estado='borrador',
            metodo_pago=data.get('metodo_pago', 'POR_DEFINIR'),
            forma_pago=data.get('forma_pago', '99'),
            notas=data.get('notas'),
            fecha_emision=fecha_hoy,
            fecha_vigencia=self.calcular_fecha_vigencia(fecha_hoy),
            creado_por=usuario_id,
            modificado_por=usuario_id,
        )
        
        self.db.add(cotizacion)
        self.db.flush()
        
        # 2. Generar número real usando el ID
        numero_real = self.generar_numero_desde_id(cotizacion.id, fecha_hoy)
        cotizacion.numero = numero_real
        cotizacion.numero_version = numero_real
        
        # 3. Agregar conceptos
        repo_concepto = RepositorioConcepto(self.db)
        for servicio_data in data.get('servicios', []):
            repo_concepto.crear(
                cotizacion_id=cotizacion.id,
                servicio_id=servicio_data['servicio_id'],
                codigo_sat=servicio_data['codigo_sat'],
                descripcion=servicio_data['descripcion'],
                unidad=servicio_data['unidad'],
                cantidad=Decimal(str(servicio_data['cantidad'])),
                precio_unitario=Decimal(str(servicio_data['precio_unitario'])),
                descuento_porcentaje=Decimal(str(servicio_data.get('descuento_porcentaje', 0))),
            )
        
        self.db.commit()
        self.db.refresh(cotizacion)
        return cotizacion

    def actualizar_notas_privadas(self, cotizacion_id: int, notas: str | None, usuario_id: str) -> Cotizacion:
        """Actualiza las notas privadas de una cotización."""
        from datetime import datetime
        
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion:
            raise LookupError("Cotización no encontrada")
        
        cotizacion.notas_privadas = notas
        cotizacion.modificado_por = usuario_id
        cotizacion.fecha_modificacion = datetime.now()
        
        self.db.add(cotizacion)
        self.db.commit()
        self.db.refresh(cotizacion)
        
        return cotizacion


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
