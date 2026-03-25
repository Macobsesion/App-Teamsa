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

    def _enriquecer_consulta(self, consulta):
        """Agrega eager loading del cliente y conceptos para evitar N+1 queries."""
        from sqlalchemy.orm import selectinload
        return consulta.options(
            selectinload(Cotizacion.cliente),
            selectinload(Cotizacion.conceptos)
        )


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
        
        Delega al ServicioAplicacionCotizacion para mantener este repositorio
        enfocado en acceso a datos, sin acoplarse directamente a RepositorioOrden.
        
        Retorna: {concepto_id: {"estado": ..., "numero_ot": ..., "orden_id": ...}}
        """
        from app.modulos.cotizaciones.cotizaciones_servicios import ServicioAplicacionCotizacion
        return ServicioAplicacionCotizacion(self.db).obtener_estado_conceptos(cotizacion_id)
    
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

