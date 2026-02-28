from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from sqlmodel import Session, select  # type: ignore

from app.base.repositorio import RepositorioCRUD
from app.base.constantes import IVA_PORCENTAJE, VIGENCIA_DIAS_DEFAULT, PREFIJO_NUMERO_COTIZACION
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.cotizaciones.enums import EstadoCotizacion
from app.base.excepciones import RecursoNoEncontradoError


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

    def listar(
        self,
        filtros: dict | None = None,
        *,
        limite: int | None = None,
        desplazamiento: int | None = None,
        orden: str | None = None,
        descendente: bool = False,
    ) -> list[Cotizacion]:
        """Lista cotizaciones con eager loading del cliente.

        Delega filtros y ordenamiento al RepositorioCRUD base y solo
        agrega el selectinload necesario para evitar N+1 queries.
        """
        from sqlalchemy.orm import selectinload

        # Construir query base con los helpers del padre
        consulta = self._construir_consulta_base(
            filtros=filtros,
            orden=orden,
            descendente=descendente,
            limite=limite,
            desplazamiento=desplazamiento,
        )
        # Eager loading: carga el cliente en la misma query
        consulta = consulta.options(selectinload(Cotizacion.cliente))
        return list(self.db.exec(consulta).all())

    def _construir_consulta_base(
        self,
        filtros: dict | None,
        orden: str | None,
        descendente: bool,
        limite: int | None,
        desplazamiento: int | None,
    ):
        """Construye la consulta base reutilizando los helpers del padre."""
        from sqlmodel import select

        consulta = select(self.modelo)
        if filtros:
            consulta = self._aplicar_filtros(consulta, filtros)
        consulta = self._aplicar_orden(consulta, orden, descendente)
        if limite is not None:
            consulta = consulta.limit(limite)
        if desplazamiento is not None:
            consulta = consulta.offset(desplazamiento)
        return consulta


    def generar_numero_desde_id(self, cotizacion_id: int, fecha_emision: date) -> str:
        """
        Genera el número de cotización basado en el ID y la fecha.
        
        Formato: COT-YYMMDD-ID
        Ejemplo: COT-260116-23 (año 26, mes 01, día 16, ID 23)
        
        Args:
            cotizacion_id: ID de la cotización en la BD
            fecha_emision: Fecha de emisión de la cotización
            
        Returns:
            Número en formato COT-YYMMDD-ID
        """
        from app.base.constantes import PREFIJO_NUMERO_COTIZACION
        
        # Formato: COT-YYMMDD-ID
        # Ejemplo: COT-260116 + 23 = COT-260116-23
        fecha_str = fecha_emision.strftime("%y%m%d")
        return f"{PREFIJO_NUMERO_COTIZACION}-{fecha_str}-{cotizacion_id}"
    
    def _pre_procesar_datos_creacion(self, datos: dict[str, Any]) -> dict[str, Any]:
        """Calcula fecha de vigencia y asigna número provisional vacío."""
        datos_procesados = datos.copy()

        if "fecha_emision" not in datos_procesados:
            datos_procesados["fecha_emision"] = date.today()

        if "fecha_vigencia" not in datos_procesados:
            fecha_emision = datos_procesados["fecha_emision"]
            if isinstance(fecha_emision, str):
                fecha_emision = date.fromisoformat(fecha_emision)
            datos_procesados["fecha_vigencia"] = fecha_emision + timedelta(days=VIGENCIA_DIAS_DEFAULT)

        # Número provisional: se sobreescribe en _post_guardar con el ID real
        if "numero" not in datos_procesados:
            datos_procesados["numero"] = ""
        if "numero_version" not in datos_procesados:
            datos_procesados["numero_version"] = ""

        return datos_procesados

    def eliminar(self, entidad_id: int) -> None:
        """
        La eliminación física está desactivada para preservar historial.
        """
        raise ValueError("La eliminación física está deshabilitada. Por favor, cambie el estado a 'Cancelada'.")
    
    def obtener_conceptos(self, cotizacion_id: int) -> list[ConceptoCotizacion]:
        """Obtiene todos los conceptos de una cotización."""
        return list(self.db.exec(
            select(ConceptoCotizacion)
            .where(ConceptoCotizacion.cotizacion_id == cotizacion_id)
            .order_by(ConceptoCotizacion.id)
        ).all())

    def obtener_estado_conceptos(self, cotizacion_id: int) -> dict[int, dict]:
        """
        Obtiene el estado de OT para cada concepto de una cotización.
        Retorna: {concepto_id: {"estado": "pendiente"|"completado", "numero_ot": ..., "orden_id": ...}}
        """
        from app.modulos.ordenes.ordenes_modelo import ConceptoOrdenTrabajo, OrdenTrabajo
        
        conceptos = self.obtener_conceptos(cotizacion_id)
        concepto_ids = [c.id for c in conceptos]
        
        estado_conceptos: dict[int, dict] = {}
        if concepto_ids:
            filas = self.db.exec(
                select(ConceptoOrdenTrabajo, OrdenTrabajo)
                .join(OrdenTrabajo, ConceptoOrdenTrabajo.orden_id == OrdenTrabajo.id)
                .where(ConceptoOrdenTrabajo.concepto_cotizacion_id.in_(concepto_ids))
            ).all()

            for c_ot, ot in filas:
                estado_conceptos[c_ot.concepto_cotizacion_id] = {
                    "estado": c_ot.estado,
                    "numero_ot": ot.numero_ot,
                    "orden_id": ot.id,
                }
        return estado_conceptos
    
    def recalcular_totales(self, cotizacion_id: int) -> None:
        """
        Recalcula subtotal, descuento, IVA y total basándose en los conceptos.
        Delega la lógica al modelo (Encapsulamiento).
        """
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion:
            return
        
        # Lógica encapsulada en el modelo
        cotizacion.recalcular_totales()
        
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


    def actualizar_notas_privadas(self, cotizacion_id: int, notas: str | None, usuario_id: str) -> Cotizacion:
        """Actualiza las notas privadas de una cotización."""
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion:
            raise RecursoNoEncontradoError("Cotización no encontrada")
        
        cotizacion.actualizar_notas_privadas(notas, usuario_id)
        
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
        # Crear concepto usando Factory Method
        concepto = ConceptoCotizacion.crear_desde_servicio(
            cotizacion_id=cotizacion_id,
            servicio_id=servicio_id,
            codigo_sat=codigo_sat,
            descripcion=descripcion,
            unidad=unidad,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            descuento_porcentaje=descuento_porcentaje
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
