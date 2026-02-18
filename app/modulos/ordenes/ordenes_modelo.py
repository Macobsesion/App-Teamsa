"""Modelo SQLModel para Ordenes de Trabajo (OT)."""
from datetime import date, time
from sqlmodel import Field, SQLModel  # type: ignore
from app.base.auditoria import AuditMixin
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    from app.base.folios import GeneradorFolio
from app.modulos.ordenes.enums import EstadoOrden

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
    
    # Estado (programada, en_curso, cancelada, cerrada)
    estado: str = Field(default=EstadoOrden.PROGRAMADA.value, index=True, description="Estado del ciclo de vida de la orden")
    
    # Información adicional
    notas_publicas: str | None = Field(default=None, description="Notas visibles en el PDF")
    notas_privadas: str | None = Field(default=None, description="Notas internas")
    
    # Relaciones
    # cotizacion: "Cotizacion" = Relationship(back_populates="orden_trabajo")

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

    # ---- FACTORY METHOD (SNAPSHOT PATTERN) ----
    @classmethod
    def crear_desde_cotizacion(
        cls,
        cotizacion: "Cotizacion",
        fecha_programada: date,
        hora_programada: str,
        duracion: int,
        usuario_id: str,
        generador_folio: "GeneradorFolio"
    ) -> "OrdenTrabajo":
        """
        Crea una Orden de Trabajo capturando una instantánea (snapshot) de los datos del cliente
        al momento de la creación.
        
        Args:
            generador_folio: Estrategia para generar el número de la OT (Strategy Pattern).
        """
        from datetime import date
        
        # Generar número de OT usando la estrategia inyectada
        numero_ot = generador_folio.generar(
            prefijo="OT", 
            id_entidad=cotizacion.id, # Usamos ID cotización como base por ahora, idealmente sería secuencia propia
            fecha=date.today()
        )
        
        # Obtener datos del cliente (Snapshot)
        cliente_nombre = "Cliente no encontrado"
        domicilio = "Sin domicilio"
        contacto = "Sin contacto"
        
        if cotizacion.cliente:
            cliente_nombre = cotizacion.cliente.nombre
            domicilio = cotizacion.cliente.direccion or domicilio
            contacto = cotizacion.cliente.contacto or contacto
            
        return cls(
            numero_ot=numero_ot,
            cotizacion_id=cotizacion.id, # type: ignore
            cliente_nombre=cliente_nombre,
            domicilio=domicilio,
            contacto=contacto,
            fecha_programada=fecha_programada,
            hora_programada=hora_programada,
            duracion=duracion,
            estado=EstadoOrden.PROGRAMADA.value,
            creado_por=usuario_id,
            modificado_por=usuario_id
        )
