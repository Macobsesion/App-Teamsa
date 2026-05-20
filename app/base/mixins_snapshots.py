"""
Mixins para Snapshots de Integridad.
Encapsulan la lógica de captura de datos históricos de catálogos (Clientes, Proveedores).
"""
from sqlmodel import Field, SQLModel
from typing import Any, Optional
from app.base.valores import Direccion

class SnapshotClienteMixin(SQLModel):
    """Encapsula campos de snapshot para Clientes."""
    cliente_nombre: Optional[str] = Field(default=None, description="Snapshot del nombre del cliente")
    cliente_rfc: Optional[str] = Field(default=None, max_length=13, description="Snapshot del RFC")
    cliente_direccion: Optional[str] = Field(default=None, description="Snapshot de la calle/dirección")
    cliente_ciudad: Optional[str] = Field(default=None, description="Snapshot de la ciudad")
    cliente_cp: Optional[str] = Field(default=None, max_length=5, description="Snapshot del CP")
    cliente_telefono: Optional[str] = Field(default=None, description="Snapshot del teléfono")
    cliente_email: Optional[str] = Field(default=None, description="Snapshot del email")

    def capturar_datos_cliente(self, cliente: Any) -> None:
        """Puebla los campos de snapshot desde una instancia de Cliente."""
        if not cliente:
            return
        self.cliente_nombre = getattr(cliente, "nombre", None)
        self.cliente_rfc = getattr(cliente, "rfc", None)
        self.cliente_direccion = getattr(cliente, "direccion", None)
        self.cliente_ciudad = getattr(cliente, "ciudad", None)
        self.cliente_cp = getattr(cliente, "cp", None)
        self.cliente_telefono = getattr(cliente, "telefono", None)
        # Priorizar email de facturación si existe
        self.cliente_email = getattr(cliente, "email_facturacion", getattr(cliente, "email", None))

    @property
    def direccion_cliente_vo(self) -> Direccion:
        """Devuelve la dirección del snapshot como un Objeto de Valor (VO)."""
        return Direccion(
            calle=self.cliente_direccion,
            ciudad=self.cliente_ciudad,
            cp=self.cliente_cp
        )
    
    @direccion_cliente_vo.setter
    def direccion_cliente_vo(self, valor: Direccion) -> None:
        """Asigna los campos del snapshot desde un VO de Dirección."""
        self.cliente_direccion = valor.calle
        self.cliente_ciudad = valor.ciudad
        self.cliente_cp = valor.cp


class SnapshotProveedorMixin(SQLModel):
    """Encapsula campos de snapshot para Proveedores."""
    proveedor_nombre: Optional[str] = Field(default=None, description="Snapshot del nombre del proveedor")
    proveedor_rfc: Optional[str] = Field(default=None, max_length=13, description="Snapshot del RFC")
    proveedor_direccion: Optional[str] = Field(default=None, description="Snapshot de la calle/dirección")
    proveedor_ciudad: Optional[str] = Field(default=None, description="Snapshot de la ciudad")
    proveedor_cp: Optional[str] = Field(default=None, max_length=5, description="Snapshot del CP")
    proveedor_telefono: Optional[str] = Field(default=None, description="Snapshot del teléfono")
    proveedor_email: Optional[str] = Field(default=None, description="Snapshot del email")

    def capturar_datos_proveedor(self, proveedor: Any) -> None:
        """Puebla los campos de snapshot desde una instancia de Proveedor."""
        if not proveedor:
            return
        self.proveedor_nombre = getattr(proveedor, "nombre", None)
        self.proveedor_rfc = getattr(proveedor, "rfc", None)
        self.proveedor_direccion = getattr(proveedor, "direccion", None)
        self.proveedor_ciudad = getattr(proveedor, "ciudad", None)
        self.proveedor_cp = getattr(proveedor, "cp", None)
        self.proveedor_telefono = getattr(proveedor, "telefono", None)
        self.proveedor_email = getattr(proveedor, "email", None)

    @property
    def direccion_proveedor_vo(self) -> Direccion:
        """Devuelve la dirección del snapshot como un Objeto de Valor (VO)."""
        return Direccion(
            calle=self.proveedor_direccion,
            ciudad=self.proveedor_ciudad,
            cp=self.proveedor_cp
        )
    
    @direccion_proveedor_vo.setter
    def direccion_proveedor_vo(self, valor: Direccion) -> None:
        """Asigna los campos del snapshot desde un VO de Dirección."""
        self.proveedor_direccion = valor.calle
        self.proveedor_ciudad = valor.ciudad
        self.proveedor_cp = valor.cp
