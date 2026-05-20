"""Modelo SQLModel para Ordenes de Trabajo (OT)."""
from datetime import date, datetime
from decimal import Decimal
from sqlmodel import Field, SQLModel, Relationship  # type: ignore
from pydantic import field_validator
from app.base.auditoria import AuditMixin
from app.base.valores import Direccion
from typing import TYPE_CHECKING, List
from app.modulos.ordenes_trabajo.ordenes_trabajo_esquemas import OrdenTrabajoBase

if TYPE_CHECKING:
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion
    from app.modulos.viaticos.viaticos_modelo import Viatico
    from app.base.folios import GeneradorFolio
from app.modulos.ordenes_trabajo.enums import EstadoOrden, EstadoConceptoOT
from app.modulos.viaticos.viaticos_modelo import ViaticoOrdenEnlace
from app.base.mixin_estado import MixinEstadoDocumento
from app.base.timezone import hoy_mexico, ahora_mexico, calcular_estado_temporal


class OrdenTrabajo(AuditMixin, MixinEstadoDocumento, OrdenTrabajoBase, table=True):
    """Orden de trabajo generada a partir de una cotización. (Regla 1.10)"""
    __tablename__ = "orden_trabajo"
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Configuración para evitar errores de Pydantic v2 con Value Objects no anotados
    model_config = {"ignored_types": (Direccion,)} # type: ignore
    
    # Identificador único: OT-{AAMMDD}-{ID_COTIZACION}
    numero_ot: str = Field(unique=True, index=True, description="Número único de la OT")
    
    # Relación con Cotización
    cotizacion_id: int = Field(foreign_key="cotizaciones.id", index=True)
    cotizacion: "Cotizacion" = Relationship(
        back_populates="ordenes",
        sa_relationship_kwargs={
            "foreign_keys": "[OrdenTrabajo.cotizacion_id]"
        }
    )
    
    # Snapshot de datos del cliente (para historial fidedigno)
    cliente_nombre: str = Field(description="Nombre del cliente al momento de crear la OT")
    
    # Propiedades que ya están en OrdenTrabajoBase:
    # fecha_programada, hora_programada, duracion, domicilio, contacto, estado, 
    # unidad_duracion, notas_publicas, notas_privadas
    
    @property
    def estado_visual(self) -> str:
        """Calcula el estado visual dinámico basado en fechas y duración.
        
        Estados visuales (NO persistidos en BD):
        - en_curso: La OT está sucediendo ahora mismo
        - fase_final: El tiempo estimado expiró pero no se ha finalizado manualmente
        """
        if self.estado != EstadoOrden.PROGRAMADA.value:
            return self.estado
        
        hoy = hoy_mexico()
        
        if self.unidad_duracion == "dias":
            from datetime import timedelta
            fecha_fin = self.fecha_programada + timedelta(days=self.duracion - 1)
            return calcular_estado_temporal(
                self.fecha_programada, 
                fecha_fin, 
                [EstadoOrden.PROGRAMADA.value], 
                self.estado
            )
        else:
            # Duración en horas
            if self.fecha_programada == hoy:
                ahora = ahora_mexico()
                try:
                    partes = self.hora_programada.split(":")
                    hora_inicio_min = int(partes[0]) * 60 + int(partes[1])
                    hora_fin_min = hora_inicio_min + (self.duracion * 60)
                    ahora_min = ahora.hour * 60 + ahora.minute
                    
                    if ahora_min < hora_inicio_min:
                        return self.estado  # Aún no empieza
                    elif ahora_min < hora_fin_min:
                        return "en_curso"
                    else:
                        return "fase_final"
                except (ValueError, AttributeError):
                    return "en_curso"
            elif hoy > self.fecha_programada:
                return "fase_final"
        
        return self.estado
    
    # Técnico asignado (opcional) — FK + snapshot para historial fidedigno
    tecnico_id: int | None = Field(default=None, foreign_key="usuario.id", index=True,
                                    description="ID del técnico asignado")
    tecnico_nombre: str | None = Field(default=None,
                                        description="Nombre del técnico al momento de asignar (snapshot)")
    
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
        from app.base.timezone import hoy_mexico
        hoy = hoy_mexico()
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
        """Crea una OT capturando snapshot del cliente."""
        cliente_nombre = "Cliente no encontrado"
        domicilio = "Sin domicilio"
        contacto = "Sin contacto"
        
        if cotizacion.cliente:
            cliente_nombre = cotizacion.cliente.nombre
            domicilio = cotizacion.cliente.direccion or domicilio
            contacto = cotizacion.cliente.contacto or contacto
            
        return cls(
            numero_ot="OT-PENDIENTE",
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
        """Asigna folio definitivo."""
        from app.base.folios import EstrategiaFolioHeredado
        estrategia = EstrategiaFolioHeredado()
        base_folio = cotizacion_numero.replace("COT-", "").replace("-", "")
        self.numero_ot = estrategia.generar(prefijo="OT", base=base_folio, secuencia=secuencia)

    def finalizar(self, usuario: str = "sistema") -> None:
        """Cambia el estado a finalizada con registro de auditoría."""
        super().finalizar(usuario=usuario)

    def cancelar(self, usuario: str = "sistema") -> None:
        """Cambia el estado a cancelada con registro de auditoría."""
        super().cancelar(usuario=usuario)


from app.base.base_detalle import BaseDetalleTransaccional

class ConceptoOrdenTrabajo(BaseDetalleTransaccional, table=True):
    """Concepto de cotización seleccionado para ejecutar en una OT."""
    __tablename__ = "concepto_orden_trabajo"
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Relación con la OT — ATENCIÓN: Apunta a la nueva tabla
    orden_id: int = Field(foreign_key="orden_trabajo.id", index=True)
    
    # Referencia al concepto original
    concepto_cotizacion_id: int = Field(
        foreign_key="conceptocotizacion.id",
        index=True,
        description="Un concepto solo puede pertenecer a una OT activa"
    )
    
    estado: str = Field(
        default=EstadoConceptoOT.PENDIENTE.value,
        index=True,
        description="Estado del concepto: pendiente o completado"
    )
    fecha_completado: datetime | None = Field(default=None, description="Cuándo se completó")
    completado_por: str | None = Field(default=None, description="Usuario que marcó como completado")

    creado_por: str = Field(description="Usuario que creó este concepto en la OT")
    fecha_creacion: datetime = Field(default_factory=ahora_mexico, description="Cuándo se creó el snapshot")

    orden: OrdenTrabajo = Relationship(back_populates="conceptos")
    concepto_cotizacion: "ConceptoCotizacion" = Relationship()
