"""Repositorio de usuarios.

Se apoya en `RepositorioCRUD` para crear/actualizar y consultas genéricas.
El método obtener_por_username ahora se reemplaza por obtener_por_campo("usuario", username).
"""
from sqlmodel import Session

from app.base.repositorio import RepositorioCRUD
from app.modulos.usuarios.usuarios_modelo import Usuario


class RepositorioUsuario(RepositorioCRUD[Usuario]):
    """Repositorio de usuarios con búsqueda por nombres, correo y área."""
    
    modelo = Usuario
    campos_filtrables = {"usuario", "rol", "id"}
    campos_busqueda = {"nombres": "icontains", "correo": "icontains", "area": "icontains"}
    campos_actualizables = {"nombres", "correo", "rol", "area", "contrasena", "modificado_por"}
    orden_por_defecto = ("id", False)

