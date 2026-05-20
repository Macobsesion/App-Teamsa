from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from sqlmodel import Session, select  # type: ignore

from app.base.repositorio import RepositorioCRUD
from app.base.constantes import IVA_PORCENTAJE, VIGENCIA_DIAS_DEFAULT, PREFIJO_NUMERO_COTIZACION
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.cotizaciones.enums import EstadoCotizacion
from app.base.excepciones import RecursoNoEncontradoError, ReglaNegocioError
from app.base.mixin_repositorio import MixinFolioMensual


class RepositorioCotizacion(MixinFolioMensual, RepositorioCRUD[Cotizacion]):
    """Repositorio de cotizaciones con lógica de numeración y cálculos."""

    modelo = Cotizacion
    prefijo_folio = PREFIJO_NUMERO_COTIZACION
    campo_fecha = "fecha_emision"

    def filtro_secuencia_extra(self) -> list:
        return [Cotizacion.cotizacion_original_id == None]
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
            selectinload(Cotizacion.conceptos),
            selectinload(Cotizacion.ordenes)
        )


    def generar_numero_desde_id(self, fecha_emision: date) -> str:
        """
        Genera el número de cotización basado en la secuencia mensual.
        
        Formato: COT-YYMMNN
        Ejemplo: COT-260401
        """
        return self.generar_folio_mensual(fecha_emision)
    
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
                nuevo_numero = self.generar_numero_desde_id(entidad.fecha_emision) # type: ignore
                entidad.numero = nuevo_numero
            
            entidad.numero_version = entidad.numero
            # Persistir cambio final sin cerrar transacción
            self.db.add(entidad)
            self.db.flush() 

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
        
        Delega al RepositorioOrden para obtener el estado de ejecución
        de las partidas vinculadas.
        
        Retorna: {concepto_id: {"estado": ..., "numero_ot": ..., "orden_id": ...}}
        """
        from app.modulos.ordenes_trabajo.ordenes_trabajo_repositorio import RepositorioOrden
        repo_ot = RepositorioOrden(self.db)
        
        conceptos = self.obtener_conceptos(cotizacion_id)
        ids = [c.id for c in conceptos if c.id is not None]
        return repo_ot.obtener_estado_por_conceptos_cotizacion(ids)
    
    def recalcular_totales(self, cotizacion_id: int) -> None:
        """
        Recalcula los totales de la cabecera consultando los conceptos frescos de la BD.
        Evita estados inconsistentes de la relación en sesión tras borrados masivos.
        """
        from app.modulos.cotizaciones.cotizaciones_modelo import ConceptoCotizacion
        
        cotizacion = self.db.get(Cotizacion, cotizacion_id)
        if not cotizacion:
            return
        
        # Consulta directa a la base de datos para obtener lo que realmente existe
        conceptos = self.db.exec(
            select(ConceptoCotizacion).where(ConceptoCotizacion.cotizacion_id == cotizacion_id)
        ).all()
        
        # Usar lógica del mixin financiero en el modelo
        cotizacion.calcular_totales(conceptos) # type: ignore
        
        self.db.add(cotizacion)
        self.db.flush()

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
        cantidad: float | Decimal, 
        precio_unitario: float | Decimal, 
        descuento_porcentaje: float | Decimal = 0,
        viatico_id: int | None = None
    ) -> ConceptoCotizacion:
        """Helper para inyectar conceptos desde otros módulos."""
        concepto = ConceptoCotizacion(
            cotizacion_id=cotizacion_id,
            servicio_id=servicio_id,
            viatico_id=viatico_id,
            codigo_sat=codigo_sat,
            descripcion=descripcion,
            unidad=unidad,
            cantidad=Decimal(str(cantidad)),
            precio_unitario=Decimal(str(precio_unitario)),
            descuento_porcentaje=Decimal(str(descuento_porcentaje)),
            importe=Decimal("0.00")
        )
        concepto.calcular_importe()
        return self.guardar(concepto)

    def eliminar_concepto(self, concepto_id: int, cotizacion_id: int) -> None:
        """Elimina un concepto y recalcula totales de la cotización."""
        concepto = self.db.get(ConceptoCotizacion, concepto_id)
        if concepto:
            self._eliminar(concepto)
            RepositorioCotizacion(self.db).recalcular_totales(cotizacion_id)

