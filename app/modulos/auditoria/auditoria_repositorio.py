from typing import Any
from sqlmodel import Session, select, desc
from app.base.repositorio import RepositorioCRUD
from app.base.logs_modelo import LogActividad

class RepositorioAuditoria(RepositorioCRUD[LogActividad]):
    modelo = LogActividad
    campos_filtrables = {"usuario", "accion", "modulo"}
    campos_busqueda = {"detalles": "icontains", "usuario": "icontains"}
    orden_por_defecto = ("fecha", True)  # Descendente por fecha

    def __init__(self, db: Session):
        super().__init__(db)

    def listar_logs(
        self, 
        filtros: dict[str, Any] | None = None, 
        limite: int = 50, 
        desplazamiento: int = 0
    ) -> list[LogActividad]:
        """Listado especializado con orden descendente forzado."""
        consulta = select(self.modelo)
        if filtros:
            consulta = self._aplicar_filtros(consulta, filtros)
        
        # Siempre ordenar por el más reciente primero
        consulta = consulta.order_by(desc(self.modelo.fecha))
        
        if limite:
            consulta = consulta.limit(limite)
        if desplazamiento:
            consulta = consulta.offset(desplazamiento)
            
        return list(self.db.exec(consulta).all())
