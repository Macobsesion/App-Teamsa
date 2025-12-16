"""Modelos SQLModel para viáticos y gastos."""
from datetime import date
from decimal import Decimal
from sqlmodel import Field, SQLModel  # type: ignore

from app.base.auditoria import AuditMixin


class Viatico(AuditMixin, SQLModel, table=True):
    """Reporte de viáticos (gastos de viaje)."""
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Numeración única y secuencial
    numero: str = Field(unique=True, index=True, description="Número de viático: VIA-00001")
    
    # Responsable y proyecto
    responsable_id: int = Field(foreign_key="usuario.id", index=True)
    proyecto: str = Field(description="Nombre delproyecto")
    cliente: str = Field(description="Cliente del proyecto")
    
    # Destino y período
    destino: str = Field(description="Ciudad/Estado de destino")
    fecha_inicio: date = Field(description="Fecha de inicio del viaje")
    fecha_fin: date = Field(description="Fecha de fin del viaje")
    dias: int = Field(default=1, description="Días del viaje (calculado)")
    
    # Estado del viático
    estado: str = Field(default="borrador", description="Estado: borrador, enviado, aprobado, rechazado, pagado")
    
    # Totales calculados por categoría
    total_transporte: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    total_alojamiento: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    total_alimentos: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    total_otros: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    total_general: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    
    # Información adicional
    notas: str | None = None
    observaciones: str | None = None


class GastoViatico(SQLModel, table=True):
    """Gasto individual dentro de un viático."""
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Relación con viático
    viatico_id: int = Field(foreign_key="viatico.id", index=True)
    
    # Categoría del gasto
    categoria: str = Field(description="Categoría: transporte, alojamiento, alimentos, otros")
    
    # Descripción del gasto
    concepto: str = Field(description="Descripción del gasto: Gasolina, Hotel, Comida, etc.")
    
    # Detalle económico
    cantidad: Decimal = Field(default=Decimal("1.00"), decimal_places=2, description="Cantidad (días, litros, etc.)")
    precio_unitario: Decimal = Field(decimal_places=2, description="Precio unitario")
    importe: Decimal = Field(decimal_places=2, description="cantidad * precio_unitario")
    
    # Comprobación
    fecha_gasto: date = Field(description="Fecha en que se realizó el gasto")
    tiene_factura: bool = Field(default=False)
    numero_factura: str | None = None
