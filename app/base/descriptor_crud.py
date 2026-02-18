"""Descriptor CRUD genérico (nombres en español)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, TypeVar, Generic, Union, Type

from pydantic import BaseModel  # type: ignore

from app.base.enrutador_crud import GanchosCRUD, construir_enrutador_crud
from app.base.utiles_esquema import (
    obtener_columnas_schema,
    obtener_campos_creables,
    obtener_campos_requeridos,
    obtener_tipos_propiedades,
)
from app.base.utilidades import filtrar_campos_permitidos

ReposType = TypeVar("ReposType")
CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)
ReadSchema = TypeVar("ReadSchema", bound=BaseModel)
ActorType = TypeVar("ActorType")


def _auditoria_creacion_default(payload: Any, actor: Any) -> dict[str, Any]:
    """Auditoría por defecto para creación: creado_por y modificado_por."""
    return {
        "creado_por": actor.usuario,
        "modificado_por": actor.usuario
    }


def _auditoria_actualizacion_default(payload: Any, actor: Any) -> dict[str, Any]:
    """Auditoría por defecto para actualización: modificado_por."""
    return {"modificado_por": actor.usuario}


@dataclass
class DescriptorCRUD(Generic[ReposType, CreateSchema, UpdateSchema, ReadSchema, ActorType]):
    """Descriptor de un módulo CRUD.

    Define la configuración declarativa para generar API y UI:
    - label, base_url, repo_factory y esquemas (read/create/update)
    - campos_editables/creables, validación de unicidad y filtros permitidos
    - metadata de frontend (columnas, mensajes y formularios opcionales)
    
    Mejoras:
    - repo_factory ahora acepta clases o funciones
    - Auditoría automática si no se especifican campos_*_extra
    """
    label: str
    base_url: str
    # Acepta AMBOS: clase directa o función factory
    repo_factory: Union[Type[ReposType], Callable[[Any], ReposType]]
    schema_read: type[ReadSchema]
    schema_create: type[CreateSchema]
    schema_update: type[UpdateSchema]
    campos_editables: Iterable[str] = field(default_factory=list)
    # None significa "usar auditoría automática", lambda vacía significa "sin auditoría"
    campos_creacion_extra: Callable[[CreateSchema, ActorType], dict[str, Any]] | None = None
    campos_actualizacion_extra: Callable[[UpdateSchema, ActorType], dict[str, Any]] | None = None
    validar_unicidad: Callable[[ReposType, CreateSchema], str | None] | None = None
    validar_actualizacion: Callable[[ReposType, UpdateSchema, int], str | None] | None = None
    filtros_permitidos: set[str] = field(default_factory=set)
    campo_busqueda: str | None = None
    topic: str | None = None
    mensajes: dict[str, str] = field(default_factory=dict)
    columnas_incluir: Iterable[str] | None = None
    columnas_excluir: Iterable[str] | None = None
    selectores: dict[str, Any] = field(default_factory=dict)
    form: list[dict[str, Any]] | None = None
    boton_crear: dict[str, Any] | None = None

    def __post_init__(self):
        """Configura auditoría automática si no se proporcionaron funciones."""
        # Si es None (no se especificó), usar auditoría automática
        if self.campos_creacion_extra is None:
            self.campos_creacion_extra = _auditoria_creacion_default
        if self.campos_actualizacion_extra is None:
            self.campos_actualizacion_extra = _auditoria_actualizacion_default
    
    def _get_repo_instance(self, db: Any) -> ReposType:
        """Obtiene instancia del repositorio, soportando clase o callable."""
        if isinstance(self.repo_factory, type):
            # Es una clase, instanciarla directamente
            return self.repo_factory(db)  # type: ignore
        else:
            # Es un callable (función), llamarlo
            return self.repo_factory(db)

    def build_hooks(self) -> GanchosCRUD[ReposType, CreateSchema, UpdateSchema, ActorType]:
        """Construye las funciones de orquestación para el ciclo CRUD.

        Por defecto:
        - preparar_creacion: usa todos los campos del schema_create (excluye None)
        - preparar_actualizacion: limita a `campos_editables`
        - extra_kwargs_*: delega en funciones opcionales para auditoría/otros
        - validar_unicidad: callback opcional provisto por el módulo
        """
        def _preparar_creacion(payload: CreateSchema, actor: ActorType) -> dict[str, Any]:
            base = payload.model_dump(exclude_none=True)
            return base

        def _preparar_actualizacion(payload: UpdateSchema, actor: ActorType) -> dict[str, Any]:
            base = filtrar_campos_permitidos(payload, self.campos_editables)
            return base

        return GanchosCRUD[
            ReposType,
            CreateSchema,
            UpdateSchema,
            ActorType,
        ](
            preparar_creacion=_preparar_creacion,
            preparar_actualizacion=_preparar_actualizacion,
            validar_unicidad=self.validar_unicidad,
            extra_kwargs_creacion=self.campos_creacion_extra,  # type: ignore
            extra_kwargs_actualizacion=self.campos_actualizacion_extra,  # type: ignore
            validar_actualizacion=self.validar_actualizacion,
        )

    # Helper para construir el API router sin repetir parámetros en los módulos
    def to_api_router(
        self,
        *,
        obtener_sesion,
        list_dependencies: list | None = None,
        write_dependency=None,
    ):
        """Crea un enrutador JSON (GET/POST/PATCH/DELETE + /metadata) listo para incluir."""
        return construir_enrutador_crud(
            prefix=self.base_url,
            tag=self.label,
            repo_factory=self.repo_factory,
            schema_read=self.schema_read,
            schema_create=self.schema_create,
            schema_update=self.schema_update,
            hooks=self.build_hooks(),
            obtener_sesion=obtener_sesion,
            list_dependencies=list_dependencies,
            write_dependency=write_dependency,
            descriptor=self,
        )

    def columnas(self, incluir: Iterable[str] | None = None, excluir: Iterable[str] | None = None):
        """Devuelve metadata de columnas a partir del schema_read.

        Permite opcionalmente limitar o excluir columnas por nombre.
        """
        incluir = incluir if incluir is not None else self.columnas_incluir
        excluir_final = set(self.columnas_excluir or [])
        if excluir:
            excluir_final.update(excluir)
        return obtener_columnas_schema(self.schema_read, incluir=incluir, excluir=excluir_final)

    def _mensajes_por_defecto(self) -> dict[str, str]:
        etiqueta = self.label
        return {
            'cargaError': f'Error al obtener {etiqueta.lower()}',
            'guardarError': f'Error al crear {etiqueta.lower()[:-1] if etiqueta.endswith("s") else etiqueta.lower()}',
            'actualizarError': f'Error al actualizar {etiqueta.lower()[:-1] if etiqueta.endswith("s") else etiqueta.lower()}',
            'eliminarError': f'Error al eliminar {etiqueta.lower()}',
            'eliminado': f'{etiqueta[:-1] if etiqueta.endswith("s") else etiqueta} eliminado',
            'confirmacionEliminar': '¿Confirma eliminar este registro?',
            'creado': f'{etiqueta[:-1] if etiqueta.endswith("s") else etiqueta} creado',
            'actualizado': f'{etiqueta[:-1] if etiqueta.endswith("s") else etiqueta} actualizado',
        }

    def frontend_config(self) -> dict[str, Any]:
        """Construye la configuración que consumen las vistas HTML (Jinja/HTMX)."""
        mensajes_finales = {**self._mensajes_por_defecto(), **(self.mensajes or {})}
        return {
            'label': self.label,
            'baseUrl': self.base_url,
            'topic': self.topic or self.base_url.strip('/').replace('/', '_'),
            'mensajes': mensajes_finales,
            'columnas': self.columnas(),
            'filtros': sorted(self.filtros_permitidos),
            'campoBusqueda': self.campo_busqueda,
            'selectores': self.selectores,
            'form': self.form,
            'editables': sorted(set(self.campos_editables)),
            'creables': obtener_campos_creables(self.schema_create),
            'required': obtener_campos_requeridos(self.schema_create),
            'propTypes': obtener_tipos_propiedades(self.schema_create),
            'botonCrear': self.boton_crear,
        }

__all__ = ["DescriptorCRUD"]
