"""Modelo SQLModel para clientes.
"""
from sqlmodel import Field, SQLModel  # type: ignore

from app.base.auditoria import AuditMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modulos.cotizaciones.cotizaciones_modelo import Cotizacion

from app.base.valores import Direccion


class Cliente(AuditMixin, SQLModel, table=True):
    """Cliente comercial."""
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Datos básicos
    nombre: str = Field(index=True)
    rfc: str | None = Field(default=None, max_length=13)
    razon_social: str | None = None
    
    # Contacto
    contacto: str | None = None
    email: str | None = None
    telefono: str | None = None
    
    # Dirección
    direccion: str | None = None
    ciudad: str | None = None
    cp: str | None = Field(default=None, max_length=5)
    
    # Estado
    activo: bool = Field(default=True)
    notas: str | None = None

    # Relaciones
    from sqlmodel import Relationship
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
