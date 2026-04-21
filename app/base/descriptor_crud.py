"""Descriptor CRUD genérico (nombres en español)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, TypeVar, Generic, Union, Type, Optional

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
class ConfiguracionUI:
    """Metadatos puramente de presentación para las vistas HTML/HTMX.
    
    Extraído del DescriptorCRUD para favorecer la Composición y el SRP.
    """
    label_singular: str | None = None
    mensajes: dict[str, str] = field(default_factory=dict)
    columnas_incluir: Iterable[str] | None = None
    columnas_excluir: Iterable[str] | None = None
    selectores: dict[str, Any] = field(default_factory=dict)
    form: list[dict[str, Any]] | None = None
    boton_crear: dict[str, Any] | None = None
    topic: str | None = None


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
    # Composición: Configuración Opcional para las vistas HTML
    config_ui: ConfiguracionUI | None = None
    # --- Campos opcionales backend (con default) ---
    campos_editables: Iterable[str] = field(default_factory=list)
    # None significa "usar auditoría automática", lambda vacía significa "sin auditoría"
    campos_creacion_extra: Callable[[CreateSchema, ActorType], dict[str, Any]] | None = None
    campos_actualizacion_extra: Callable[[UpdateSchema, ActorType], dict[str, Any]] | None = None
    validar_unicidad: Callable[[ReposType, CreateSchema], str | None] | None = None
    validar_actualizacion: Callable[[ReposType, UpdateSchema, int], str | None] | None = None
    filtros_permitidos: set[str] = field(default_factory=set)
    campo_busqueda: str | None = None

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
        """Devuelve metadata de columnas a partir del schema_read."""
        ui = self.config_ui or ConfiguracionUI()
        incluir = incluir if incluir is not None else ui.columnas_incluir
        excluir_final = set(ui.columnas_excluir or [])
        if excluir:
            excluir_final.update(excluir)
        return obtener_columnas_schema(self.schema_read, incluir=incluir, excluir=excluir_final)

    def _singular(self) -> str:
        """Devuelve el nombre singular del recurso para mensajes."""
        ui = self.config_ui or ConfiguracionUI()
        if ui.label_singular:
            return ui.label_singular
        # Fallback: quitar 's' final si la tiene
        return self.label[:-1] if self.label.lower().endswith("s") else self.label

    def _mensajes_por_defecto(self) -> dict[str, str]:
        etiqueta = self.label
        singular = self._singular()
        return {
            'cargaError': f'Error al obtener {etiqueta.lower()}',
            'guardarError': f'Error al crear {singular.lower()}',
            'actualizarError': f'Error al actualizar {singular.lower()}',
            'eliminarError': f'Error al eliminar {singular.lower()}',
            'eliminado': f'{singular} eliminado',
            'confirmacionEliminar': '¿Confirma eliminar este registro?',
            'creado': f'{singular} creado',
            'actualizado': f'{singular} actualizado',
        }

    def frontend_config(self) -> dict[str, Any]:
        """Construye la configuración que consumen las vistas HTML (Jinja/HTMX)."""
        ui = self.config_ui or ConfiguracionUI()
        mensajes_finales = {**self._mensajes_por_defecto(), **(ui.mensajes or {})}
        topic = ui.topic or self.base_url.strip('/').split('/')[-1].replace('-', '_')
        return {
            'label': self.label,
            'baseUrl': self.base_url,
            'topic': topic,
            'mensajes': mensajes_finales,
            'columnas': self.columnas(),
            'filtros': sorted(self.filtros_permitidos),
            'campoBusqueda': self.campo_busqueda,
            'selectores': ui.selectores,
            'form': ui.form,
            'editables': sorted(set(self.campos_editables)),
            'creables': obtener_campos_creables(self.schema_create),
            'required': obtener_campos_requeridos(self.schema_create),
            'propTypes': obtener_tipos_propiedades(self.schema_create),
            'botonCrear': ui.boton_crear,
        }

__all__ = ["DescriptorCRUD", "ConfiguracionUI"]
