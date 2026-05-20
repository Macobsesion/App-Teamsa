"""Modelo SQLModel para Ordenes de Trabajo (OT)."""
from datetime import date, datetime
from decimal import Decimal
from sqlmodel import Field, SQLModel, Relationship  # type: ignore
from pydantic import field_validator
from app.base.auditoria import AuditMixin
from app.base.valores import Direccion
from typing import TYPE_CHECKING, List
if TYPE_CHECKING:
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    from app.modulos.viaticos.viaticos_modelo import Viatico
    from app.base.folios import GeneradorFolio
from app.modulos.ordenes.enums import EstadoOrden, EstadoConceptoOT
from app.modulos.viaticos.viaticos_modelo import ViaticoOrdenEnlace


class OrdenTrabajo(AuditMixin, SQLModel, table=True):
    """Orden de trabajo generada a partir de una cotización."""
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Identificador único: OT-{AAMMDD}-{ID_COTIZACION}
    numero_ot: str = Field(unique=True, index=True, description="Número único de la OT")
    
    # Relación con Cotización
    cotizacion_id: int = Field(foreign_key="cotizaciones.id", index=True)
    
    # Snapshot de datos del cliente (para historial fidedigno)
    cliente_nombre: str = Field(description="Nombre del cliente al momento de crear la OT")
    domicilio: str = Field(description="Domicilio del servicio")
    contacto: str = Field(description="Nombre del contacto")
    
    # Agendamiento
    fecha_programada: date = Field(description="Día del servicio")
    hora_programada: str = Field(description="Hora de inicio programada (HH:MM)")
    duracion: int = Field(default=1, description="Duración estimada en horas")
    
    # Estado (programada, en_curso, cancelada, finalizada)
    estado: str = Field(default=EstadoOrden.PROGRAMADA.value, index=True, description="Estado del ciclo de vida de la orden")
    
    # Técnico asignado (opcional) — FK + snapshot para historial fidedigno
    tecnico_id: int | None = Field(default=None, foreign_key="usuario.id", index=True,
                                    description="ID del técnico asignado")
    tecnico_nombre: str | None = Field(default=None,
                                        description="Nombre del técnico al momento de asignar (snapshot)")
    
    # Información adicional
    notas_publicas: str | None = Field(default=None, description="Notas visibles en el PDF")
    notas_privadas: str | None = Field(default=None, description="Notas internas")
    
    # Relación con conceptos seleccionados
    conceptos: List["ConceptoOrdenTrabajo"] = Relationship(back_populates="orden")
    
    # Relación Muchos a Muchos con Viáticos
    viaticos: List["Viatico"] = Relationship(back_populates="rutas_ot", link_model=ViaticoOrdenEnlace)


    # ---- PROPIEDADES COMPUESTAS (Value Objects) ----

    @property
    def direccion_cliente_vo(self) -> Direccion:
        """Devuelve la dirección del snapshot como un Objeto de Valor."""
        return Direccion(
            calle=self.domicilio,
            # OT no tiene ciudad/cp en base, se podrían añadir o dejar opcionales
        )
    
    @direccion_cliente_vo.setter
    def direccion_cliente_vo(self, valor: Direccion) -> None:
        """Asigna la dirección del snapshot descomponiendo el VO."""
        self.domicilio = valor.calle

    # ---- PROPIEDADES DE ESTADO (POLIMORFISMO) ----
    @property
    def estado_enum(self) -> EstadoOrden:
        return EstadoOrden(self.estado)

    @property
    def es_editable(self) -> bool:
        return self.estado_enum.es_editable

    @property
    def es_cancelable(self) -> bool:
        return self.estado_enum.es_cancelable

    @property
    def esta_en_viaje(self) -> bool:
        if not self.viaticos:
            return False
        from datetime import date
        hoy = date.today()
        for v in self.viaticos:
            if v.estado not in ["cancelado", "borrador"]:
                if v.fecha_salida and v.fecha_regreso:
                    if v.fecha_salida <= hoy <= v.fecha_regreso:
                        return True
        return False

    @classmethod
    def crear_desde_cotizacion(
        cls,
        cotizacion: "Cotizacion",
        fecha_programada: date,
        hora_programada: str,
        duracion: int,
        usuario_id: str,
        generador_folio: "GeneradorFolio",
        tecnico_id: int | None = None,
        tecnico_nombre: str | None = None,
    ) -> "OrdenTrabajo":
        """
        Crea una Orden de Trabajo capturando una instantánea (snapshot) de los datos del cliente
        al momento de la creación.
        
        NOTA: el numero_ot se asigna con folio temporal y debe actualizarse con
        `asignar_folio(generador_folio)` DESPUÉS de que la BD asigne el ID (post-flush).
        """
        cliente_nombre = "Cliente no encontrado"
        domicilio = "Sin domicilio"
        contacto = "Sin contacto"
        
        if cotizacion.cliente:
            cliente_nombre = cotizacion.cliente.nombre
            domicilio = cotizacion.cliente.direccion or domicilio
            contacto = cotizacion.cliente.contacto or contacto
            
        return cls(
            numero_ot="OT-PENDIENTE",   # folio temporal; se actualiza post-flush con asignar_folio()
            cotizacion_id=cotizacion.id,  # type: ignore
            cliente_nombre=cliente_nombre,
            domicilio=domicilio,
            contacto=contacto,
            fecha_programada=fecha_programada,
            hora_programada=hora_programada,
            duracion=duracion,
            estado=EstadoOrden.PROGRAMADA.value,
            tecnico_id=tecnico_id,
            tecnico_nombre=tecnico_nombre,
            creado_por=usuario_id,
            modificado_por=usuario_id
        )

    def asignar_folio(self, cotizacion_numero: str, secuencia: int) -> None:
        """
        Asigna el numero_ot definitivo basado en el número de cotización y secuencia.
        """
        from app.base.folios import EstrategiaFolioHeredado
        estrategia = EstrategiaFolioHeredado()
        
        # 'COT-260307-B' -> '260307B'
        base_folio = cotizacion_numero.replace("COT-", "").replace("-", "")
        self.numero_ot = estrategia.generar(prefijo="OT", base=base_folio, secuencia=secuencia)


from app.base.base_detalle import BaseDetalleTransaccional

class ConceptoOrdenTrabajo(BaseDetalleTransaccional, table=True):
    """
    Concepto de cotización seleccionado para ejecutar en una OT.
    
    Snapshot Pattern: copia los datos del concepto al momento de crear la OT
    para mantener historial fidedigno aunque el concepto original cambie.
    
    Estado: solo avanza de pendiente → completado (irreversible).
    """
    __tablename__ = "concepto_orden_trabajo"
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Relación con la OT
    orden_id: int = Field(foreign_key="ordentrabajo.id", index=True)
    
    # Referencia al concepto original (unique: un concepto solo puede estar en una OT)
    concepto_cotizacion_id: int = Field(
        foreign_key="conceptocotizacion.id",
        index=True,
        unique=True,
        description="Un concepto solo puede pertenecer a una OT activa"
    )
    
    # Snapshot de datos al momento de crear la OT / heredado: descripcion, unidad, cantidad, precio_unitario, importe
    
    # Estado irreversible: pendiente → completado
    estado: str = Field(
        default=EstadoConceptoOT.PENDIENTE.value,
        index=True,
        description="Estado del concepto: pendiente o completado (irreversible)"
    )
    fecha_completado: datetime | None = Field(default=None, description="Cuándo se completó")
    completado_por: str | None = Field(default=None, description="Usuario que marcó como completado")

    # Auditoría del snapshot
    creado_por: str = Field(description="Usuario que creó este concepto en la OT")
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, description="Cuándo se creó el snapshot")

    # Relación
    orden: OrdenTrabajo = Relationship(back_populates="conceptos")
