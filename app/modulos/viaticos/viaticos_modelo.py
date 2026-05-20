from datetime import date
from pydantic import model_validator
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, SQLModel, Relationship  # type: ignore

from app.base.documentos_modelo import BaseDocumento
from app.modulos.viaticos.enums import EstadoViatico
from app.modulos.viaticos.viaticos_esquemas import ViaticoBase

if TYPE_CHECKING:
    from app.modulos.clientes.clientes_modelo import Cliente
    from app.modulos.usuarios.usuarios_modelo import Usuario
    from app.modulos.ordenes_trabajo.ordenes_trabajo_modelo import OrdenTrabajo
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion

class ViaticoOrdenEnlace(SQLModel, table=True):
    """Enlace Muchos a Muchos entre Viáticos y Órdenes de Trabajo."""
    __tablename__ = "viatico_orden_enlace"
    
    viatico_id: Optional[int] = Field(default=None, foreign_key="viaticos.id", primary_key=True)
    orden_id: Optional[int] = Field(default=None, foreign_key="orden_trabajo.id", primary_key=True)


class Viatico(ViaticoBase, BaseDocumento, table=True):
    """Registro de viáticos con desglose global."""
    __tablename__ = "viaticos"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # MIXIN/BASE: ViaticoBase ya incluye cliente_id, responsable_id, proyecto, etc. 
    # y ahora también SnapshotClienteMixin (cliente_nombre, cliente_rfc, etc.)

    @model_validator(mode='after')
    def validar_fechas_coherentes(self) -> "Viatico":
        if self.fecha_salida and self.fecha_regreso:
            if self.fecha_regreso < self.fecha_salida:
                raise ValueError("La fecha de regreso no puede ser anterior a la fecha de salida")
        return self

    
    # El campo 'total' es heredado de BaseDocumento y será calculado (auto sum)
    # subtotal e iva los dejaremos en 0 para viaticos, usando el 'total' como neto.

    # Relaciones
    cliente: "Cliente" = Relationship()
    responsable: "Usuario" = Relationship()
    cotizacion: Optional["Cotizacion"] = Relationship()
    rutas_ot: list["OrdenTrabajo"] = Relationship(link_model=ViaticoOrdenEnlace, back_populates="viaticos")

    @property
    def estado_enum(self) -> "EstadoViatico":
        from app.modulos.viaticos.enums import EstadoViatico
        return EstadoViatico(self.estado)

    @property
    def estado_visual(self) -> str:
        """Calcula el estado visual dinámico basado en las fechas del viaje."""
        from app.base.timezone import calcular_estado_temporal
        from app.modulos.viaticos.enums import EstadoViatico
        
        estados_dinamicos = [
            EstadoViatico.BORRADOR.value, 
            EstadoViatico.SOLICITADO.value, 
            EstadoViatico.APROBADO.value
        ]
        
        if self.fecha_salida and self.fecha_regreso:
            return calcular_estado_temporal(
                self.fecha_salida, 
                self.fecha_regreso, 
                estados_dinamicos, 
                self.estado
            )
        
        return self.estado

    def finalizar(self, usuario: str = "sistema") -> None:
        """Cambia el estado a finalizada con registro de auditoría."""
        super().finalizar(usuario=usuario)

    def cancelar(self, usuario: str = "sistema") -> None:
        """Cambia el estado a cancelada con registro de auditoría."""
        super().cancelar(usuario=usuario)
