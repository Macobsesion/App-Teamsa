"""Modelo simplificado de Viáticos."""
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, SQLModel, Relationship  # type: ignore

from app.base.documentos_modelo import BaseDocumento
from app.modulos.viaticos.enums import EstadoViatico

if TYPE_CHECKING:
    from app.modulos.clientes.clientes_modelo import Cliente
    from app.modulos.usuarios.usuarios_modelo import Usuario
    from app.modulos.ordenes.ordenes_modelo import OrdenTrabajo
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion

class ViaticoOrdenEnlace(SQLModel, table=True):
    """Enlace Muchos a Muchos entre Viáticos y Órdenes de Trabajo."""
    __tablename__ = "viatico_orden_enlace"
    
    viatico_id: Optional[int] = Field(default=None, foreign_key="viaticos.id", primary_key=True)
    orden_id: Optional[int] = Field(default=None, foreign_key="ordentrabajo.id", primary_key=True)


class Viatico(BaseDocumento, table=True):
    """Registro de viáticos con desglose global."""
    __tablename__ = "viaticos"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Meta
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    responsable_id: int = Field(foreign_key="usuario.id", index=True)
    proyecto: Optional[str] = Field(default=None, description="Nombre o descripción del viaje")
    
    # Detalles del viaje
    personas: int = Field(default=1)
    tipo_transporte: Optional[str] = Field(default=None, description="Camión, Avión, Taxi, Auto Rentado")
    cotizacion_id: int = Field(foreign_key="cotizaciones.id", index=True)
    origen: Optional[str] = Field(default=None)
    destino: Optional[str] = Field(default=None)
    fecha_salida: Optional[date] = Field(default=None)
    fecha_regreso: Optional[date] = Field(default=None)

    # Costos Reducidos
    costo_transporte: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    costo_alojamiento: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    costo_alimentos: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    costo_otros: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    
    notas_desglose: Optional[str] = Field(default=None, description="Desglose rápido sin estructura")
    
    # El campo 'total' es heredado de BaseDocumento y será calculado (auto sum)
    # subtotal e iva los dejaremos en 0 para viaticos, usando el 'total' como neto.

    # Relaciones
    cliente: "Cliente" = Relationship()
    responsable: "Usuario" = Relationship()
    cotizacion: Optional["Cotizacion"] = Relationship()
    rutas_ot: list["OrdenTrabajo"] = Relationship(link_model=ViaticoOrdenEnlace, back_populates="viaticos")

    @property
    def estado_enum(self) -> EstadoViatico:
        return EstadoViatico(self.estado)
