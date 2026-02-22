from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from sqlmodel import Session, select  # type: ignore

from app.base.repositorio import RepositorioCRUD
from app.base.constantes import IVA_PORCENTAJE, VIGENCIA_DIAS_DEFAULT, PREFIJO_NUMERO_COTIZACION
from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion, ConceptoCotizacion
from app.modulos.cotizaciones.enums import EstadoCotizacion


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
        """Calcula fecha de vigencia y número temporal por defecto."""
        datos_procesados = datos.copy()
        
        # Fecha de emisión y vigencia
        if "fecha_emision" not in datos_procesados:
            datos_procesados["fecha_emision"] = date.today()
            
        if "fecha_vigencia" not in datos_procesados:
            fecha_emision = datos_procesados["fecha_emision"]
            if isinstance(fecha_emision, str):
                 # Si viene como str por Pydantic/JSON
                 fecha_emision = date.fromisoformat(fecha_emision)
            datos_procesados["fecha_vigencia"] = fecha_emision + timedelta(days=VIGENCIA_DIAS_DEFAULT)

        # Número temporal si no existe
        if "numero" not in datos_procesados:
            datos_procesados["numero"] = "TEMP-PENDING"
        if "numero_version" not in datos_procesados:
            datos_procesados["numero_version"] = "TEMP-PENDING"
            
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
