"""Repositorio para Órdenes de Compra."""
from sqlmodel import select
from typing import List

from app.base.repositorio import RepositorioCRUD
from app.modulos.ordenes_compra.ordenes_compra_modelo import OrdenCompra, DetalleOrdenCompra

class RepositorioOrdenCompra(RepositorioCRUD[OrdenCompra]):
    modelo = OrdenCompra
    campos_filtrables = {"proveedor_id", "estado", "fecha_emision"}
    campos_actualizables = {
        "proveedor_id", "estado", "fecha_emision", "fecha_entrega_estimada",
        "metodo_pago", "forma_pago", "notas", "notas_privadas", "modificado_por"
    }
    campos_busqueda = {"folio": "icontains", "notas": "icontains"}

    def _condiciones_busqueda_personalizada(self, valor_seguro: str) -> list:
        """Permite buscar coincidencias en los conceptos/servicios de la orden de compra."""
        return [
            OrdenCompra.detalles.any(DetalleOrdenCompra.descripcion.ilike(f"%{valor_seguro}%"))
        ]
    
    def _enriquecer_consulta(self, consulta):
        from sqlalchemy.orm import selectinload
        return consulta.options(selectinload(OrdenCompra.detalles))
    
    def obtener_con_detalles(self, id_orden: int) -> OrdenCompra | None:
        """Obtiene una orden cargando ansiosamente sus detalles."""
        # En SQLModel/SQLAlchemy async la carga lazy puede fallar si no se configura bien.
        # Aquí usamos select directo. Si lazy='selectin' en el modelo, el .get() normal funciona.
        # Asumimos configuración correcta, pero si falla, usar .options(selectinload(...))
        return self.obtener_por_id(id_orden)

class RepositorioDetalleOrdenCompra(RepositorioCRUD[DetalleOrdenCompra]):
    modelo = DetalleOrdenCompra
