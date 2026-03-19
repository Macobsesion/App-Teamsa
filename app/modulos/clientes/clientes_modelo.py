"""Modelo SQLModel para clientes.
"""
from sqlmodel import Field, SQLModel, Relationship  # type: ignore

from app.base.auditoria import AuditMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion

from app.base.valores import Direccion
from app.modulos.clientes.clientes_esquemas import ClienteBase


class Cliente(ClienteBase, AuditMixin, table=True):
    """Cliente comercial."""
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Relaciones
    cotizaciones: list["Cotizacion"] = Relationship(back_populates="cliente")
    
    # ---- PROPIEDADES COMPUESTAS (Value Objects) ----
    
    @property
    def direccion_vo(self) -> Direccion:
        """Devuelve la dirección como un Objeto de Valor."""
        return Direccion(
            calle=self.direccion,
            ciudad=self.ciudad,
            cp=self.cp
        )
    
    @direccion_vo.setter
    def direccion_vo(self, valor: Direccion) -> None:
        """Asigna la dirección descomponiendo el Objeto de Valor en columnas planas."""
        self.direccion = valor.calle
        self.ciudad = valor.ciudad
        self.cp = valor.cp
