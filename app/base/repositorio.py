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

from sqlmodel import Session, SQLModel, select, or_  # type: ignore
from sqlalchemy import asc, desc  # type: ignore
import logging

TModelo = TypeVar("TModelo", bound=SQLModel)


from app.base.excepciones import RecursoNoEncontradoError
from app.base.eventos import BusEventos

logger = logging.getLogger("teamsa.repositorio")

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
            self.db.flush()  # Asegura que se disparen las restricciones antes del commit
            self.db.commit()
        except Exception as e:
            logger.error(f"Error en transaccion {self.modelo.__name__}: {str(e)}")
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

    def _pre_procesar_datos_creacion(self, datos: dict[str, Any]) -> dict[str, Any]:
        """Hook para modificar datos crudos antes de crear la instancia."""
        return datos

    def _pre_procesar_cambios(self, cambios: Mapping[str, Any]) -> Mapping[str, Any]:
        """Hook para modificar el diccionario de cambios antes de aplicarlos."""
        return cambios

    def _pre_guardar(self, entidad: TModelo, es_nuevo: bool) -> None:
        """Hook para validaciones o cálculos sobre la entidad antes del commit."""
        pass

    def _validar_eliminacion(self, entidad: TModelo) -> None:
        """
        Hook para validar si una entidad puede ser eliminada.
        Debe lanzar ReglaNegocioError si el borrado está prohibido por dependencias.
        """
        pass

    def _post_guardar(self, entidad: TModelo, es_nuevo: bool) -> None:
        """Hook para acciones posteriores al guardado (logs, notificaciones)."""
        pass

    def _enriquecer_consulta(self, consulta):
        """Hook para que subclases enriquezcan la consulta base (ej: eager loading).

        Sobrescribir en el repositorio hijo para agregar selectinload, joinedload, etc.
        sin necesidad de reimplementar el método listar() completo.

        Example::

            def _enriquecer_consulta(self, consulta):
                return consulta.options(selectinload(MiModelo.relacion))
        """
        return consulta

    def _sanitizar_busqueda(self, valor: str) -> str:
        """
        Escapa caracteres especiales de SQL LIKE para prevenir inyección.
        
        Los wildcards SQL LIKE (%, _) permiten búsquedas amplias no autorizadas:
        - '%' = cualquier cantidad de caracteres
        - '_' = exactamente un carácter
        
        Un atacante podría buscar '%' para obtener todos los registros,
        o usar '_%' para patrones amplios que revelan información.
        
        Escapamos también backslash para evitar bypass del escape.
        
        Args:
            valor: String de búsqueda del usuario
            
        Returns:
            String sanitizado seguro para ILIKE
            
        Example:
            >>> _sanitizar_busqueda("a%b_c")
            'a\\%b\\_c'  # Los wildcards ahora son literales
        """
        if not isinstance(valor, str):
            valor = str(valor)
        
        # Escapar backslash primero para evitar bypass del escape
        valor = valor.replace("\\", "\\\\")
        # Escapar wildcards SQL LIKE
        valor = valor.replace("%", "\\%")
        valor = valor.replace("_", "\\_")
        return valor

    def _condiciones_busqueda_personalizada(self, valor_seguro: str) -> list:
        """Hook para que las subclases agreguen condiciones OR personalizadas (ej. búsquedas en relaciones)."""
        return []

    def aplicar_seguridad_filtro(self, filtros: Mapping[str, Any], actor: Any) -> Mapping[str, Any]:
        """
        Hook para inyectar filtros obligatorios basados en el actor (usuario logueado).
        Se usa para seguridad a nivel de fila (ej: técnicos solo ven sus OTs).
        
        Args:
            filtros: Diccionario de filtros actual.
            actor: Usuario logueado (modelo completo de DB o esquema identity).
            
        Returns:
            Mapping actualizado con los filtros de seguridad aplicados.
        """
        return filtros

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
        # Hook de extensión: permite eager loading u otras transformaciones
        consulta = self._enriquecer_consulta(consulta)
        if limite is not None:
            consulta = consulta.limit(limite)
        if desplazamiento is not None:
            consulta = consulta.offset(desplazamiento)
        return list(self.db.exec(consulta).all())

    def contar(self, filtros: Mapping[str, Any] | None = None) -> int:
        """Devuelve el número total de registros que coinciden con los filtros."""
        from sqlmodel import func
        consulta = select(func.count()).select_from(self.modelo)
        if filtros:
            consulta = self._aplicar_filtros(consulta, filtros)
        resultado = self.db.exec(consulta).one_or_none()
        return resultado or 0

    def crear(self, datos: Mapping[str, Any]) -> TModelo:
        """Crea la entidad usando los datos recibidos."""
        # Asegurar que los datos sean tratados como un dict para el hook
        datos_dict = dict(datos)
        datos_procesados = self._pre_procesar_datos_creacion(datos_dict)
        
        # BLINDAJE FINAL (Repositorio): Asegurar que los campos de auditoría no sean nulos
        if not datos_procesados.get("creado_por"):
            datos_procesados["creado_por"] = datos_dict.get("creado_por") or "SISTEMA"
        if not datos_procesados.get("modificado_por"):
            datos_procesados["modificado_por"] = datos_dict.get("modificado_por") or "SISTEMA"
            
        print(f">>> REPO_CREAR - Audit Check: {datos_procesados.get('creado_por')}", flush=True)

        entidad = self.modelo(**datos_procesados)
        self._pre_guardar(entidad, es_nuevo=True)
        guardada = self.guardar(entidad)
        self._post_guardar(guardada, es_nuevo=True)
        
        # Emitir Evento de Dominio Desacoplado
        BusEventos.publicar(f"{self.modelo.__name__}.creado", guardada)
        
        return guardada

    def guardar(self, entidad: TModelo) -> TModelo:
        """Persiste una entidad existente o nueva en la base de datos de forma segura."""
        return self._guardar(entidad)

    def actualizar(self, entidad_id: int, cambios: Mapping[str, Any]) -> TModelo:
        entidad = self.db.get(self.modelo, entidad_id)
        if not entidad:
            raise RecursoNoEncontradoError(f"{self.modelo.__name__} con id {entidad_id} no encontrado")
        
        cambios_procesados = self._pre_procesar_cambios(cambios)
        
        cambios_permitidos = {
            campo: valor for campo, valor in cambios_procesados.items() if campo in self.campos_actualizables
        }
        self._aplicar_cambios(entidad, cambios_permitidos)
        
        self._pre_guardar(entidad, es_nuevo=False)
        guardada = self.guardar(entidad)
        self._post_guardar(guardada, es_nuevo=False)
        
        # Emitir Evento de Dominio Desacoplado
        BusEventos.publicar(f"{self.modelo.__name__}.actualizado", guardada)
        
        return guardada

    def eliminar(self, entidad_id: int) -> None:
        entidad = self.db.get(self.modelo, entidad_id)
        if not entidad:
            raise RecursoNoEncontradoError(f"{self.modelo.__name__} con id {entidad_id} no encontrado")
        
        logger.info(f"Eliminando físicamente {self.modelo.__name__} ID: {entidad_id}")
        
        # Validar dependencias de negocio antes de tocar la BD
        self._validar_eliminacion(entidad)
        
        self._eliminar(entidad)
        logger.info(f"Eliminación de {self.modelo.__name__} {entidad_id} completada.")
        
        # Emitir Evento de Dominio Desacoplado
        BusEventos.publicar(f"{self.modelo.__name__}.eliminado", entidad)

    def obtener_por_id(self, entidad_id: int) -> TModelo:
        """Obtiene una entidad por su ID o lanza RecursoNoEncontradoError HTTP 404."""
        entidad = self.db.get(self.modelo, entidad_id)
        if not entidad:
            raise RecursoNoEncontradoError(f"El recurso con id {entidad_id} no fue encontrado.")
        return entidad

    def obtener_por_campo(self, campo: str, valor: Any) -> TModelo | None:
        """
        Busca una entidad por un campo específico con valor exacto.
        
        Este método genérico reemplaza la necesidad de crear métodos
        personalizados como obtener_por_nombre, obtener_por_clave, etc.
        
        Args:
            campo: Nombre del campo a buscar (ej: 'nombre', 'clave', 'usuario')
            valor: Valor exacto a buscar
            
        Returns:
            La primera entidad que coincide o None si no existe
            
        Raises:
            ValueError: Si el campo no existe en el modelo
            
        Example:
            >>> repo.obtener_por_campo("nombre", "Acme Corp")
            <Cliente(id=1, nombre="Acme Corp")>
        """
        columna = getattr(self.modelo, campo, None)
        if columna is None:
            raise ValueError(f"Campo '{campo}' no existe en {self.modelo.__name__}")
        
        consulta = select(self.modelo).where(columna == valor)
        return self.db.exec(consulta).first()

    # ---- helpers internos ----
    def _aplicar_filtros(self, consulta, filtros: Mapping[str, Any]):
        condiciones_or = []
        
        for campo, valor in filtros.items():
            if not valor and valor != 0:
                continue

            # Caso especial: Búsqueda multi-campo genérica
            if campo == "q":
                valor_seguro = self._sanitizar_busqueda(str(valor))
                if self.campos_busqueda:
                    for c_busqueda, operador in self.campos_busqueda.items():
                        col = getattr(self.modelo, c_busqueda, None)
                        if col is None: continue
                        
                        if operador == "icontains":
                            condiciones_or.append(col.ilike(f"%{valor_seguro}%"))
                        elif operador == "startswith":
                            condiciones_or.append(col.ilike(f"{valor_seguro}%"))
                        elif operador == "endswith":
                            condiciones_or.append(col.ilike(f"%{valor_seguro}"))
                
                cond_pers = self._condiciones_busqueda_personalizada(valor_seguro)
                if cond_pers:
                    condiciones_or.extend(cond_pers)
                continue

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
                valor_seguro = self._sanitizar_busqueda(str(valor))
                
                if operador == "icontains":
                    consulta = consulta.where(columna.ilike(f"%{valor_seguro}%"))
                elif operador == "startswith":
                    consulta = consulta.where(columna.ilike(f"{valor_seguro}%"))
                elif operador == "endswith":
                    consulta = consulta.where(columna.ilike(f"%{valor_seguro}"))
        
        if condiciones_or:
            consulta = consulta.where(or_(*condiciones_or))
            
        return consulta

    def _aplicar_orden(self, consulta, orden: str | None, descendente: bool | None):
        campo = orden or (self.orden_por_defecto[0] if self.orden_por_defecto else None)
        if not campo:
            return consulta
        columna = getattr(self.modelo, campo, None)
        if columna is None:
            return consulta
        return consulta.order_by(desc(columna) if descendente else asc(columna))
