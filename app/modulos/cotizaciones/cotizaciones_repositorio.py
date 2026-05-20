from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from sqlmodel import Session, select  # type: ignore

from app.base.repositorio import RepositorioCRUD
from app.base.constantes import IVA_PORCENTAJE, VIGENCIA_DIAS_DEFAULT, PREFIJO_NUMERO_COTIZACION
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.cotizaciones.enums import EstadoCotizacion
from app.base.excepciones import RecursoNoEncontradoError, ReglaNegocioError


class RepositorioCotizacion(RepositorioCRUD[Cotizacion]):
    """Repositorio de cotizaciones con lógica de numeración y cálculos."""

    modelo = Cotizacion
    campos_filtrables = {"estado", "cliente_id"}
    campos_actualizables = {
        "cliente_id", "estado", "notas", "notas_privadas", "metodo_pago",
        "descuento_porcentaje", "modificado_por"
    }
    campos_busqueda = {"numero": "icontains", "cliente_nombre": "icontains", "cliente_rfc": "icontains"}
    orden_por_defecto = ("numero", True)  # Descendente (más reciente primero)

    def _condiciones_busqueda_personalizada(self, valor_seguro: str) -> list:
        """Permite buscar coincidencias en los conceptos/servicios de la cotización."""
        return [
            Cotizacion.conceptos.any(ConceptoCotizacion.descripcion.ilike(f"%{valor_seguro}%"))
        ]

    def _enriquecer_consulta(self, consulta):
        """Agrega eager loading del cliente y conceptos para evitar N+1 queries."""
        from sqlalchemy.orm import selectinload
        return consulta.options(
            selectinload(Cotizacion.cliente),
            selectinload(Cotizacion.conceptos)
        )


    def _obtener_siguiente_secuencia_mensual(self, fecha: date) -> int:
        """
        Calcula el siguiente número secuencial para el mes y año de la fecha dada.
        """
        from sqlalchemy import func
        from sqlmodel import and_
        
        primer_dia_mes = date(fecha.year, fecha.month, 1)
        if fecha.month == 12:
            primer_dia_sgte_mes = date(fecha.year + 1, 1, 1)
        else:
            primer_dia_sgte_mes = date(fecha.year, fecha.month + 1, 1)
            
        # Contar cuántas cotizaciones existen en este mes
        # Filtramos por fecha_emision dentro del mes
        conteo = self.db.exec(
            select(func.count(Cotizacion.id))
            .where(
                and_(
                    Cotizacion.fecha_emision >= primer_dia_mes,
                    Cotizacion.fecha_emision < primer_dia_sgte_mes,
                    Cotizacion.cotizacion_original_id == None # Solo contamos 'madres', no versiones
                )
            )
        ).first() or 0
        
        return conteo + 1

    def generar_numero_desde_id(self, cotizacion_id: int, fecha_emision: date) -> str:
        """
        Genera el número de cotización basado en la secuencia mensual.
        
        Formato: COT-YYMMNN
        Ejemplo: COT-260401
        """
        from app.base.folios import EstrategiaFolioMensual
        from app.base.constantes import PREFIJO_NUMERO_COTIZACION
        
        secuencia = self._obtener_siguiente_secuencia_mensual(fecha_emision)
        estrategia = EstrategiaFolioMensual()
        return estrategia.generar(PREFIJO_NUMERO_COTIZACION, fecha_emision, secuencia)
    
    def _pre_procesar_datos_creacion(self, datos: dict[str, Any]) -> dict[str, Any]:
        """Calcula fecha de vigencia y garantiza folio/número provisionales."""
        import uuid
        datos_procesados = datos.copy()

        if "fecha_emision" not in datos_procesados:
            datos_procesados["fecha_emision"] = date.today()

        if "fecha_vigencia" not in datos_procesados:
            fecha_emision = datos_procesados["fecha_emision"]
            if isinstance(fecha_emision, str):
                fecha_emision = date.fromisoformat(fecha_emision)
            datos_procesados["fecha_vigencia"] = fecha_emision + timedelta(days=VIGENCIA_DIAS_DEFAULT)

        # Campos obligatorios para BaseDocumento (temporales hasta _post_guardar)
        if not datos_procesados.get("folio"):
            datos_procesados["folio"] = str(uuid.uuid4())
        
        if not datos_procesados.get("numero"):
            datos_procesados["numero"] = "TEMP-" + datos_procesados["folio"][:8]
        if not datos_procesados.get("numero_version"):
            datos_procesados["numero_version"] = datos_procesados["numero"]

        return datos_procesados

    def _post_guardar(self, entidad: Cotizacion, es_nuevo: bool) -> None:
        """Asigna el número definitivo basado en el ID real tras la creación."""
        if es_nuevo:
            # Generar número real: COT-YYMMNN
            # Si es una versión (tiene cotizacion_original_id), hereda el número pero con letra
            if entidad.cotizacion_original_id:
                madre = self.obtener_por_id(entidad.cotizacion_original_id)
                entidad.numero = f"{madre.numero}-{entidad.version_letra}"
            else:
                nuevo_numero = self.generar_numero_desde_id(entidad.id, entidad.fecha_emision) # type: ignore
                entidad.numero = nuevo_numero
            
            entidad.numero_version = entidad.numero
            # Persistir cambio final
            self.db.add(entidad)
            self.db.commit()
            self.db.refresh(entidad)

    def eliminar(self, entidad_id: int) -> None:
        """
        La eliminación física está desactivada para preservar historial.
        """
        raise ReglaNegocioError("La eliminación física está deshabilitada. Por favor, cambie el estado a 'Cancelada'.")
    
    def obtener_conceptos(self, cotizacion_id: int) -> list[ConceptoCotizacion]:
        """Obtiene todos los conceptos de una cotización."""
        return list(self.db.exec(
            select(ConceptoCotizacion)
            .where(ConceptoCotizacion.cotizacion_id == cotizacion_id)
            .order_by(ConceptoCotizacion.id)
        ).all())

    def obtener_estado_conceptos(self, cotizacion_id: int) -> dict[int, dict]:
        """
        Obtiene el estado de ejecución (OT) para cada concepto de una cotización.
        
        Delega al ServicioCotizaciones para mantener este repositorio
        enfocado en acceso a datos, sin acoplarse directamente a RepositorioOrden.
        
        Retorna: {concepto_id: {"estado": ..., "numero_ot": ..., "orden_id": ...}}
        """
        from app.modulos.cotizaciones.cotizaciones_servicios import ServicioCotizaciones
        return ServicioCotizaciones(self.db).obtener_estado_conceptos(cotizacion_id)
    
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
        return self.guardar(cotizacion)


class RepositorioConcepto(RepositorioCRUD[ConceptoCotizacion]):
    """Repositorio para conceptos de cotización.

    Hereda de RepositorioCRUD para usar la gestión de transacciones del padre.
    El hook _post_guardar dispara el recálculo de totales de la cotización padre.
    """

    modelo = ConceptoCotizacion

    def _post_guardar(self, entidad: ConceptoCotizacion, es_nuevo: bool) -> None:
        """Recalcula los totales de la cotización después de guardar el concepto."""
        RepositorioCotizacion(self.db).recalcular_totales(entidad.cotizacion_id)

    def crear_concepto(
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
        """Crea un concepto y recalcula totales de la cotización padre."""
        concepto = ConceptoCotizacion.crear_desde_servicio(
            cotizacion_id=cotizacion_id,
            servicio_id=servicio_id,
            codigo_sat=codigo_sat,
            descripcion=descripcion,
            unidad=unidad,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            descuento_porcentaje=descuento_porcentaje,
        )
        return self.guardar(concepto)

    def eliminar_concepto(self, concepto_id: int, cotizacion_id: int) -> None:
        """Elimina un concepto y recalcula totales de la cotización."""
        concepto = self.db.get(ConceptoCotizacion, concepto_id)
        if concepto:
            self._eliminar(concepto)
            RepositorioCotizacion(self.db).recalcular_totales(cotizacion_id)

