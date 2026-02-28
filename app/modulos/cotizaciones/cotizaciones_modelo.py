"""Modelos SQLModel para cotizaciones y conceptos."""
from datetime import date, datetime
from decimal import Decimal
from sqlmodel import Field, SQLModel, Relationship  # type: ignore
from typing import TYPE_CHECKING

from app.base.auditoria import AuditMixin

if TYPE_CHECKING:
    from app.modulos.clientes.clientes_modelo import Cliente


from app.modulos.cotizaciones.enums import EstadoCotizacion
from app.base.documentos_modelo import BaseDocumento
from app.base.mixins_financieros import MixinDetalleFinanciero

class Cotizacion(BaseDocumento, table=True):
    """Cotizacion comercial con conceptos dinámicos."""
    __tablename__ = "cotizaciones"
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Numeración
    numero: str = Field(unique=True, index=True, description="Número con versión: COT-00001 o COT-00001-B")
    numero_version: str = Field(unique=True, index=True, description="Alias de numero (para compatibilidad)")
    
    # Versionamiento
    version_letra: str | None = Field(default=None, description="Letra de versión: None=original, B, C, etc.")
    cotizacion_original_id: int | None = Field(default=None, foreign_key="cotizaciones.id", index=True, description="ID de la cotización original si es versión")
    
    # Datos de negocio específicos
    fecha_vigencia: date | None = Field(default=None, description="Fecha límite de validez de la oferta")
    
    # Relación con cliente
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    
    # Estado (flujo de negocio)
    # MIXIN: BaseDocumento ya incluye fecha_emision, estado, metodo_pago, forma_pago, notas, notas_privadas, folio
    
    # Relationship (para cargar conceptos)
    cliente: "Cliente" = Relationship(back_populates="cotizaciones")
    conceptos: list["ConceptoCotizacion"] = Relationship(back_populates="cotizacion")

    # ---- PROPIEDADES DE ESTADO (POLIMORFISMO) ----
    @property
    def estado_enum(self) -> EstadoCotizacion:
        """Devuelve el estado como objeto Enum."""
        return EstadoCotizacion(self.estado)

    @property
    def puede_crear_ot(self) -> bool:
        return self.estado_enum.permite_crear_ot


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

    def actualizar_notas_privadas(self, notas: str | None, usuario_id: str) -> None:
        """Encapsula la mutación de notas privadas."""
        from datetime import datetime
        self.notas_privadas = notas
        self.modificado_por = usuario_id
        self.fecha_modificacion = datetime.now()


class ConceptoCotizacion(MixinDetalleFinanciero, SQLModel, table=True):
    """Concepto (item/línea) de una cotización."""
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Relación con cotización
    cotizacion_id: int = Field(foreign_key="cotizaciones.id", index=True)
    
    # Relación con servicio (opcional, para trazabilidad)
    servicio_id: int | None = Field(default=None, foreign_key="servicio.id", index=True)
    
    # Datos del servicio copiados al momento de crear (snapshot)
    codigo_sat: str = Field(description="Código SAT del producto/servicio")
    descripcion: str = Field(description="Descripción del concepto")
    unidad: str = Field(description="Unidad de medida: pieza, hora, etc.")
    codigo_unidad: str = Field(default="H87", description="Código de unidad SAT")
    
    # MIXIN: cantidad, precio_unitario, descuento_porcentaje, importe ya están definidos
    
    # Relationships
    cotizacion: "Cotizacion" = Relationship(back_populates="conceptos")

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
        cotizacion_id: int | None = None
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
            importe=Decimal("0.00") # Se recalcula abajo
        )
        # Usar lógica del mixin
        instancia.calcular_importe()
        return instancia

