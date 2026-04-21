"""Modelos SQLModel para cotizaciones y conceptos."""
from datetime import date, datetime
from decimal import Decimal
from sqlmodel import Field, SQLModel, Relationship  # type: ignore
from pydantic import field_validator, model_validator
from typing import TYPE_CHECKING, Optional

from app.base.auditoria import AuditMixin
from app.base.valores import Direccion

if TYPE_CHECKING:
    from app.modulos.clientes.clientes_modelo import Cliente
    from app.modulos.viaticos.viaticos_modelo import Viatico
    from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo

from app.modulos.cotizaciones.cotizaciones_esquemas import CotizacionBase
from app.modulos.cotizaciones.enums import EstadoCotizacion
from app.base.documentos_modelo import BaseDocumento
from app.base.mixins_financieros import MixinDetalleFinanciero

class Cotizacion(CotizacionBase, BaseDocumento, table=True):
    """Cotizacion comercial con conceptos dinámicos."""
    __tablename__ = "cotizaciones"
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Configuración para evitar errores de Pydantic v2 con Value Objects no anotados en el namespace
    model_config = {"ignored_types": (Direccion,)} # type: ignore
    
    @model_validator(mode="after")
    def validar_fechas(self) -> "Cotizacion":
        if self.fecha_vigencia and self.fecha_emision:
            if self.fecha_vigencia < self.fecha_emision:
                raise ValueError("La fecha de vigencia no puede ser anterior a la de emisión")
        return self
    
    # MIXIN/BASE: CotizacionBase ya incluye numero, version, snapshots de cliente, etc.
    # MIXIN: BaseDocumento ya incluye fecha_emision, estado, metodo_pago, forma_pago, notas, notas_privadas, folio
    
    # Relationship (para cargar conceptos)
    cliente: "Cliente" = Relationship(back_populates="cotizaciones")
    conceptos: list["ConceptoCotizacion"] = Relationship(back_populates="cotizacion")
    ordenes: list["OrdenTrabajo"] = Relationship(back_populates="cotizacion")

    # ---- PROPIEDADES COMPUESTAS (Value Objects) ----

    # MIXIN/BASE: CotizacionBase ya incluye numero, version, snapshots de cliente, etc.
    # MIXIN: BaseDocumento ya incluye fecha_emision, estado, metodo_pago, forma_pago, notas, notas_privadas, folio
    @property
    def estado_enum(self) -> EstadoCotizacion:
        """Devuelve el estado como objeto Enum."""
        return EstadoCotizacion(self.estado)

    @property
    def puede_crear_ot(self) -> bool:
        return self.estado_enum.permite_crear_ot

    @property
    def estado_visual(self) -> str:
        """Determina el estado visual de la cotización basado en sus OTs activas."""
        # Regla: Solo si tiene OTs activas y alguna está 'En curso' o 'en_curso'
        if self.estado in [EstadoCotizacion.ACEPTADA.value, EstadoCotizacion.PROGRAMADA.value]:
            for ot in self.ordenes:
                if ot.estado_visual == "en_curso" or ot.estado == "en_curso":
                    return "en_curso"
        return self.estado


    # ---- MÉTODOS DE DOMINIO (ENCAPSULAMIENTO) ----
    def recalcular_totales(self) -> None:
        """
        Actualiza los totales de la cotización basándose en sus conceptos actuales.
        Usa lógica del MixinDocumentoFinanciero.
        """
        self.calcular_totales(self.conceptos) # type: ignore

    def actualizar_vigencia(self) -> None:
        """Calcula y actualiza la fecha de vigencia basada en la fecha de emisión."""
        from datetime import timedelta
        # Podríamos mover la constante VIGENCIA_DIAS_DEFAULT aquí o importarla
        from app.base.constantes import VIGENCIA_DIAS_DEFAULT
        
        if self.fecha_emision:
            self.fecha_vigencia = self.fecha_emision + timedelta(days=VIGENCIA_DIAS_DEFAULT)

    @classmethod
    def crear_desde_wizard(
        cls, 
        cliente: "Cliente", 
        metodo_pago: str, 
        forma_pago: str, 
        notas: str | None = None, 
        usuario_id: str = "sistema"
    ) -> "Cotizacion":
        """
        Factory method para crear una cotización capturando el snapshot del cliente.
        Garantiza que folio y numero sean únicos temporalmente mediante UUID.
        """
        import uuid
        from app.modulos.cotizaciones.enums import EstadoCotizacion
        
        # Generar identificadores temporales únicos para evitar colisiones en el flush
        uid = str(uuid.uuid4())
        folio_temp = f"TEMP-{uid}"
        numero_temp = f"TEMP-{uid[:8]}"

        instancia = cls(
            cliente_id=cliente.id,  # type: ignore
            metodo_pago=metodo_pago,
            forma_pago=forma_pago,
            notas=notas,
            estado=EstadoCotizacion.BORRADOR.value,
            folio=folio_temp,
            numero=numero_temp,
            numero_version=numero_temp,
            fecha_emision=date.today(),
            creado_por=usuario_id,
        )
        instancia.capturar_datos_cliente(cliente)
        instancia.actualizar_vigencia()
        return instancia


from app.base.base_detalle import BaseDetalleTransaccional

class ConceptoCotizacion(BaseDetalleTransaccional, table=True):
    """Concepto (item/línea) de una cotización."""
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Relación con cotización
    cotizacion_id: int = Field(foreign_key="cotizaciones.id", index=True)
    
    # Relación con servicio (opcional, para trazabilidad)
    servicio_id: int | None = Field(default=None, foreign_key="servicio.id", index=True)
    
    # Relación con viático (opcional, para automatización de cancelaciones)
    viatico_id: int | None = Field(default=None, foreign_key="viaticos.id", index=True)
    
    # Datos del servicio copiados al momento de crear (snapshot)
    codigo_sat: str = Field(description="Código SAT del producto/servicio")
    codigo_unidad: str = Field(default="H87", description="Código de unidad SAT")
    
    # BaseDetalleTransaccional ya incluye: descripcion, unidad, cantidad, precio_unitario, importe, descuento_porcentaje
    
    # Relationships
    cotizacion: "Cotizacion" = Relationship(back_populates="conceptos")
    viatico: Optional["Viatico"] = Relationship()

    @classmethod
    def crear_desde_servicio(
        cls,
        servicio_id: int | None,
        codigo_sat: str,
        descripcion: str,
        unidad: str,
        cantidad: Decimal,
        precio_unitario: Decimal,
        descuento_porcentaje: Decimal = Decimal("0.00"),
        cotizacion_id: int | None = None,
        viatico_id: int | None = None
    ) -> "ConceptoCotizacion":
        """
        Factory Method para crear un concepto encapsulando la lógica de cálculo inicial.
        """
        instancia = cls(
            cotizacion_id=cotizacion_id, # type: ignore
            servicio_id=servicio_id,
            codigo_sat=codigo_sat,
            descripcion=descripcion,
            unidad=unidad,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            descuento_porcentaje=descuento_porcentaje,
            viatico_id=viatico_id,
            importe=Decimal("0.00") # Se recalcula abajo
        )
        # Usar lógica del mixin
        instancia.calcular_importe()
        return instancia

