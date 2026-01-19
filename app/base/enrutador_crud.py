"""Enrutador CRUD genérico (nombres en español)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Response, status, Query  # type: ignore
from fastapi import Request
from pydantic import BaseModel  # type: ignore
from sqlmodel import Session  # type: ignore

from app.base.repositorio import RepositorioCRUD

RepoT = TypeVar("RepoT", bound=RepositorioCRUD)
ReadSchemaT = TypeVar("ReadSchemaT", bound=BaseModel)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)
ActorT = TypeVar("ActorT")


@dataclass
class GanchosCRUD(Generic[RepoT, CreateSchemaT, UpdateSchemaT, ActorT]):
    """Colección de funciones de orquestación para el ciclo CRUD.

    - preparar_creacion: transforma el payload de creación (p. ej., normaliza campos)
    - preparar_actualizacion: filtra y transforma cambios permitidos en PATCH
    - extra_kwargs_*: agrega kwargs adicionales (auditoría, hashing, etc.)
    - validar_unicidad: retorna un mensaje de conflicto si el recurso ya existe
    """

    preparar_creacion: Callable[[CreateSchemaT, ActorT], dict[str, Any]]
    preparar_actualizacion: Callable[[UpdateSchemaT, ActorT], dict[str, Any]]
    extra_kwargs_creacion: Callable[[CreateSchemaT, ActorT], dict[str, Any]] = lambda _payload, _actor: {}
    extra_kwargs_actualizacion: Callable[[UpdateSchemaT, ActorT], dict[str, Any]] = lambda _payload, _actor: {}
    validar_unicidad: Optional[Callable[[RepoT, CreateSchemaT], Optional[str]]] = None
    # Validación opcional para actualización (JSON API): retorna mensaje de error o None
    validar_actualizacion: Optional[Callable[[RepoT, UpdateSchemaT, int], Optional[str]]] = None


def construir_enrutador_crud(
    *,
    prefix: str,
    tag: str,
    repo_factory: Callable[[Session], RepoT],
    schema_read: type[ReadSchemaT],
    schema_create: type[CreateSchemaT],
    schema_update: type[UpdateSchemaT],
    hooks: GanchosCRUD[RepoT, CreateSchemaT, UpdateSchemaT, ActorT],
    obtener_sesion: Callable[..., Session],
    list_dependencies: Optional[list[Depends]] = None,
    write_dependency: Optional[Callable[..., ActorT]] = None,
    descriptor: Optional[Any] = None,
) -> APIRouter:
    """Crea un APIRouter CRUD (JSON) para un módulo.

    Parámetros clave:
    - prefix/tag: prefijo de rutas y etiqueta OpenAPI.
    - repo_factory: construye el repositorio con una `Session`.
    - schema_read/create/update: esquemas Pydantic tipados.
    - hooks: funciones para transformar payloads y validar unicidad.
    - obtener_sesion: dependencia que produce `Session` (yield).
    - list_dependencies: dependencias comunes para todas las rutas (p. ej. autenticación).
    - write_dependency: dependencia que produce el actor/autorización para mutaciones.
    - descriptor: si está presente, habilita `/metadata` y filtrado controlado en listar.
    """
    router = APIRouter(prefix=prefix, tags=[tag], dependencies=list_dependencies or [])

    def _get_repo(db: Session) -> RepoT:
        return repo_factory(db)

    @router.get("/", response_model=list[schema_read])
    def listar(
        request: Request,
        limite: int | None = Query(None, ge=1, le=1000),
        desplazamiento: int | None = Query(None, ge=0),
        orden: str | None = Query(None),
        descendente: bool = Query(False),
        q: str | None = Query(None),
        db: Session = Depends(obtener_sesion),
    ):
        repo = _get_repo(db)
        filtros: dict[str, Any] = {}
        if descriptor:
            for clave in descriptor.filtros_permitidos:
                if clave in request.query_params:
                    filtros[clave] = request.query_params.get(clave)
            if descriptor.campo_busqueda and q:
                filtros[descriptor.campo_busqueda] = q
        else:
            for clave, valor in request.query_params.items():
                if clave not in {"limite", "desplazamiento", "orden", "descendente", "q"}:
                    filtros[clave] = valor
        return repo.listar(
            filtros,
            limite=limite,
            desplazamiento=desplazamiento,
            orden=orden,
            descendente=descendente,
        )

    @router.post("/", response_model=schema_read)
    def crear(
        payload: schema_create,
        db: Session = Depends(obtener_sesion),
        actor: ActorT = Depends(write_dependency) if write_dependency else None,
    ):
        repo = _get_repo(db)
        if hooks.validar_unicidad:
            conflicto = hooks.validar_unicidad(repo, payload)
            if conflicto:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=conflicto)
        datos = hooks.preparar_creacion(payload, actor)  # type: ignore[arg-type]
        extras = hooks.extra_kwargs_creacion(payload, actor)  # type: ignore[arg-type]
        combinado = {**datos, **(extras or {})}
        return repo.crear(**combinado)

    @router.patch("/{entidad_id}", response_model=schema_read)
    def actualizar(
        entidad_id: int,
        payload: schema_update,
        db: Session = Depends(obtener_sesion),
        actor: ActorT = Depends(write_dependency) if write_dependency else None,
    ):
        repo = _get_repo(db)
        # Validación opcional de actualización (suave): devolver 400 con detalle
        if hooks.validar_actualizacion is not None:
            msg = hooks.validar_actualizacion(repo, payload, entidad_id)
            if msg:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        cambios = hooks.preparar_actualizacion(payload, actor)  # type: ignore[arg-type]
        if not cambios:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay cambios válidos para aplicar",
            )
        extras = hooks.extra_kwargs_actualizacion(payload, actor)  # type: ignore[arg-type]
        combinado = {**cambios, **(extras or {})}
        try:
            return repo.actualizar(entidad_id, combinado)
        except LookupError as exc:  # pragma: no cover
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado") from exc

    @router.get("/{entidad_id}", response_model=schema_read)
    def obtener(
        entidad_id: int,
        db: Session = Depends(obtener_sesion),
    ):
        repo = _get_repo(db)
        try:
            entidad = repo.obtener_por_id(entidad_id)
            if entidad is None:
                 raise LookupError("Recurso no encontrado")
            return entidad
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado") from exc


    @router.delete("/{entidad_id}", status_code=status.HTTP_204_NO_CONTENT)
    def eliminar(
        entidad_id: int,
        db: Session = Depends(obtener_sesion),
        actor: ActorT = Depends(write_dependency) if write_dependency else None,
    ):
        repo = _get_repo(db)
        try:
            repo.eliminar(entidad_id)
        except LookupError as exc:  # pragma: no cover
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado") from exc
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if descriptor:
        @router.get("/metadata")
        def obtener_metadata():
            # Compatibilidad: algunos descriptores pueden seguir usando el nombre antiguo
            if hasattr(descriptor, "configuracion_frontend"):
                return descriptor.configuracion_frontend()
            # Compatibilidad final: intentar método antiguo si el nuevo no existe
            return descriptor.frontend_config()

    return router

__all__ = ["construir_enrutador_crud", "GanchosCRUD"]
