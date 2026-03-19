"""
Dependencias inyectables para el módulo de Órdenes.
Utiliza el sistema de DI de FastAPI para construir repositorios complejos.
"""
from fastapi import Depends
from sqlmodel import Session

from app.nucleo.base_datos import obtener_sesion_bd
from app.base.folios import EstrategiaFolioFechaId, GeneradorFolio
from app.modulos.ordenes.ordenes_repositorio import RepositorioOrden

def obtener_generador_folios() -> GeneradorFolio:
    """
    Provee la estrategia de generación de folios.
    Se puede sobreescribir con dependency_overrides en tests.
    """
    return EstrategiaFolioFechaId()

def obtener_repo_ordenes(
    db: Session = Depends(obtener_sesion_bd),
    generador: GeneradorFolio = Depends(obtener_generador_folios)
) -> RepositorioOrden:
    """
    Factory que ensambla el RepositorioOrden con todas sus dependencias.
    """
    return RepositorioOrden(db, generador_folio=generador)

from app.modulos.ordenes.ordenes_servicios import ServicioOrdenes

def obtener_servicio_ordenes(
    db: Session = Depends(obtener_sesion_bd),
    generador: GeneradorFolio = Depends(obtener_generador_folios)
) -> ServicioOrdenes:
    """
    Factory que provee el Servicio de Dominio para operaciones complejas.
    """
    return ServicioOrdenes(db, generador)
