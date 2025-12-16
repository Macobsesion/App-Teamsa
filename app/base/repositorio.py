# Herramientas genéricas para repositorios basados en SQLModel.
#
# Este repositorio CRUD genérico encapsula:
# - Transacciones (commit/rollback) seguras.
# - Listados con filtros (igualdad, IN y búsqueda icontains/starts/ends) y ordenación.
# - Operaciones crear/actualizar/eliminar con whitelists de campos.
from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any, Callable, Generic, Iterable, Iterator, TypeVar

from sqlmodel import Session, SQLModel, select  # type: ignore
from sqlalchemy import asc, desc  # type: ignore

TModelo = TypeVar("TModelo", bound=SQLModel)


class RepositorioCRUD(Generic[TModelo]):
    """Repositorio CRUD genérico con filtros y actualizaciones limitadas."""

    modelo: type[TModelo]
    campos_filtrables: set[str] = set()
    campos_actualizables: set[str] = set()
    campos_busqueda: dict[str, str] = {}
    filtros_personalizados: dict[str, Callable[[Any, Any], Any]] = {}
    orden_por_defecto: tuple[str, bool] | None = ("id", False)

    def __init__(self, db: Session):
        self.db = db

    # ---- utilidades transaccionales ----
    @contextmanager
    def _transaccion(self) -> Iterator[None]:
        try:
            yield
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _guardar(self, entidad: TModelo) -> TModelo:
        with self._transaccion():
            self.db.add(entidad)
        self.db.refresh(entidad)
        return entidad

    def _eliminar(self, entidad: TModelo) -> None:
        with self._transaccion():
            self.db.delete(entidad)

    def _aplicar_cambios(self, entidad: TModelo, cambios: Mapping[str, Any]) -> None:
        for campo, valor in cambios.items():
            setattr(entidad, campo, valor)

    # ---- operaciones públicas ----
    def listar(
        self,
        filtros: Mapping[str, Any] | None = None,
        *,
        limite: int | None = None,
        desplazamiento: int | None = None,
        orden: str | None = None,
        descendente: bool = False,
    ) -> list[TModelo]:
        consulta = select(self.modelo)
        if filtros:
            consulta = self._aplicar_filtros(consulta, filtros)
        consulta = self._aplicar_orden(consulta, orden, descendente)
        if limite is not None:
            consulta = consulta.limit(limite)
        if desplazamiento is not None:
            consulta = consulta.offset(desplazamiento)
        return list(self.db.exec(consulta).all())

    def crear(self, **datos: Any) -> TModelo:
        """Crea la entidad usando los datos recibidos."""
        entidad = self.modelo(**datos)
        return self._guardar(entidad)

    def actualizar(self, entidad_id: int, cambios: Mapping[str, Any]) -> TModelo:
        entidad = self.db.get(self.modelo, entidad_id)
        if not entidad:
            raise LookupError(f"{self.modelo.__name__} no encontrado")
        cambios_permitidos = {
            campo: valor for campo, valor in cambios.items() if campo in self.campos_actualizables
        }
        self._aplicar_cambios(entidad, cambios_permitidos)
        return self._guardar(entidad)

    def eliminar(self, entidad_id: int) -> None:
        entidad = self.db.get(self.modelo, entidad_id)
        if not entidad:
            raise LookupError(f"{self.modelo.__name__} no encontrado")
        self._eliminar(entidad)

    # ---- helpers internos ----
    def _aplicar_filtros(self, consulta, filtros: Mapping[str, Any]):
        for campo, valor in filtros.items():
            if campo in self.filtros_personalizados:
                consulta = self.filtros_personalizados[campo](consulta, valor)
                continue
            columna = getattr(self.modelo, campo, None)
            if columna is None:
                continue
            if campo in self.campos_filtrables:
                if isinstance(valor, (list, tuple, set)):
                    consulta = consulta.where(columna.in_(valor))
                else:
                    consulta = consulta.where(columna == valor)
            elif campo in self.campos_busqueda:
                operador = self.campos_busqueda[campo]
                if operador == "icontains":
                    consulta = consulta.where(columna.ilike(f"%{valor}%"))
                elif operador == "startswith":
                    consulta = consulta.where(columna.ilike(f"{valor}%"))
                elif operador == "endswith":
                    consulta = consulta.where(columna.ilike(f"%{valor}"))
        return consulta

    def _aplicar_orden(self, consulta, orden: str | None, descendente: bool | None):
        campo = orden or (self.orden_por_defecto[0] if self.orden_por_defecto else None)
        if not campo:
            return consulta
        columna = getattr(self.modelo, campo, None)
        if columna is None:
            return consulta
        return consulta.order_by(desc(columna) if descendente else asc(columna))
