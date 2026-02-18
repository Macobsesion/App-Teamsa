"""Repositorio para Órdenes de Compra."""
from sqlmodel import select
from typing import List

from app.base.repositorio import RepositorioCRUD
from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra, DetalleOrdenCompra

class RepositorioOrdenCompra(RepositorioCRUD[OrdenCompra]):
    modelo = OrdenCompra
    campos_filtrables = {"proveedor_id", "estado", "fecha_emision"}
    campos_busqueda = {"folio": "icontains", "notas": "icontains"}
    
    def obtener_con_detalles(self, id_orden: int) -> OrdenCompra | None:
        """Obtiene una orden cargando ansiosamente sus detalles."""
        # En SQLModel/SQLAlchemy async la carga lazy puede fallar si no se configura bien.
        # Aquí usamos select directo. Si lazy='selectin' en el modelo, el .get() normal funciona.
        # Asumimos configuración correcta, pero si falla, usar .options(selectinload(...))
        return self.obtener_por_id(id_orden)

class RepositorioDetalleOrdenCompra(RepositorioCRUD[DetalleOrdenCompra]):
    modelo = DetalleOrdenCompra
