import logging
from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, TypeVar, Dict
from fastapi import APIRouter, Depends, Response, status, Query, Body, Request
from pydantic import BaseModel
from sqlmodel import Session

from app.base.repositorio import RepositorioCRUD
from app.base.excepciones import ReglaNegocioError, RecursoNoEncontradoError
from app.base.logs_servicio import ServicioLogs

RepoT = TypeVar("RepoT", bound=RepositorioCRUD)
ReadSchemaT = TypeVar("ReadSchemaT", bound=BaseModel)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)
ActorT = TypeVar("ActorT")

logger = logging.getLogger("teamsa.api_crud")

@dataclass
class GanchosCRUD(Generic[RepoT, CreateSchemaT, UpdateSchemaT, ActorT]):
    """Colección de funciones de orquestación para el ciclo CRUD."""
    preparar_creacion: Callable[[CreateSchemaT, ActorT], dict[str, Any]]
    preparar_actualizacion: Callable[[UpdateSchemaT, ActorT], dict[str, Any]]
    extra_kwargs_creacion: Callable[[CreateSchemaT, ActorT], dict[str, Any]] = lambda _p, _a: {}
    extra_kwargs_actualizacion: Callable[[UpdateSchemaT, ActorT], dict[str, Any]] = lambda _p, _a: {}
    validar_unicidad: Optional[Callable[[RepoT, CreateSchemaT], Optional[str]]] = None
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
    create_dependency: Optional[Callable[..., ActorT]] = None,
    update_dependency: Optional[Callable[..., ActorT]] = None,
    delete_dependency: Optional[Callable[..., ActorT]] = None,
    descriptor: Optional[Any] = None,
) -> APIRouter:
    """Crea un APIRouter CRUD (JSON) para un módulo con dependencias granulares."""
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
        actor: ActorT = Depends(create_dependency) if create_dependency else Depends(update_dependency),
    ):
        # Nota: Usamos create_dependency o update_dependency como fallback para obtener el actor si existe
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
        
        # Aplicar filtros de seguridad si el repositorio lo soporta
        filtros = repo.aplicar_seguridad_filtro(filtros, actor)
        
        return repo.listar(filtros, limite=limite, desplazamiento=desplazamiento, orden=orden, descendente=descendente)

    @router.post("/", response_model=schema_read)
    def crear(
        payload_dict: Dict[str, Any] = Body(...),
        db: Session = Depends(obtener_sesion),
        actor: ActorT = Depends(create_dependency) if create_dependency else None,
    ):
        try:
            payload = schema_create(**payload_dict)
        except Exception as e:
            raise ReglaNegocioError(str(e))

        repo = _get_repo(db)
        if hooks.validar_unicidad:
            conflicto = hooks.validar_unicidad(repo, payload)
            if conflicto: raise ReglaNegocioError(conflicto)
            
        datos = hooks.preparar_creacion(payload, actor)
        extras = (hooks.extra_kwargs_creacion(payload, actor) or {}).copy()
        
        # BLINDAJE API: Asegurar auditoría
        u_login = getattr(actor, "usuario", None) or getattr(actor, "nombre", None) or "SISTEMA"
        if not extras.get("creado_por"): extras["creado_por"] = u_login
        if not extras.get("modificado_por"): extras["modificado_por"] = u_login
        
        print(f">>> AUDITORIA API - Actor: {u_login}", flush=True)
        
        res = repo.crear({**datos, **extras})
        
        # Registrar Log de Actividad
        ServicioLogs.registrar(
            db, 
            usuario=u_login, 
            accion="CREAR", 
            modulo=tag.lower(), 
            detalles=str(getattr(res, "id", ""))
        )
        
        return res

    @router.patch("/{entidad_id}", response_model=schema_read)
    def actualizar(
        entidad_id: int,
        payload_dict: Dict[str, Any] = Body(...),
        db: Session = Depends(obtener_sesion),
        actor: ActorT = Depends(update_dependency) if update_dependency else None,
    ):
        try:
            payload = schema_update(**payload_dict)
        except Exception as e:
            raise ReglaNegocioError(str(e))

        repo = _get_repo(db)
        if hooks.validar_actualizacion:
            msg = hooks.validar_actualizacion(repo, payload, entidad_id)
            if msg: raise ReglaNegocioError(msg)
            
        cambios = hooks.preparar_actualizacion(payload, actor)
        if not cambios: raise ReglaNegocioError("No hay cambios válidos para aplicar")
        extras = hooks.extra_kwargs_actualizacion(payload, actor)
        res = repo.actualizar(entidad_id, {**cambios, **(extras or {})})
        
        # Registrar Log de Actividad
        u_login = getattr(actor, "usuario", None) or getattr(actor, "nombre", None) or "SISTEMA"
        ServicioLogs.registrar(
            db, 
            usuario=u_login, 
            accion="EDITAR", 
            modulo=tag.lower(), 
            detalles=str(entidad_id)
        )
        
        return res

    @router.get("/{entidad_id}", response_model=schema_read)
    def obtener(entidad_id: int, db: Session = Depends(obtener_sesion)):
        repo = _get_repo(db)
        entidad = repo.obtener_por_id(entidad_id)
        if entidad is None: raise RecursoNoEncontradoError("Recurso no encontrado")
        return entidad

    @router.delete("/{entidad_id}", status_code=status.HTTP_204_NO_CONTENT)
    def eliminar(
        entidad_id: int,
        db: Session = Depends(obtener_sesion),
        _actor: ActorT = Depends(delete_dependency) if delete_dependency else None,
    ):
        repo = _get_repo(db)
        repo.eliminar(entidad_id)
        
        # Registrar Log de Actividad
        u_login = getattr(_actor, "usuario", None) or getattr(_actor, "nombre", None) or "SISTEMA"
        ServicioLogs.registrar(
            db, 
            usuario=u_login, 
            accion="ELIMINAR", 
            modulo=tag.lower(), 
            detalles=str(entidad_id)
        )
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if descriptor:
        @router.get("/metadata")
        def obtener_metadata():
            if hasattr(descriptor, "configuracion_frontend"):
                return descriptor.configuracion_frontend()
            return descriptor.frontend_config()

    return router

__all__ = ["construir_enrutador_crud", "GanchosCRUD"]
