"""Repositorio de usuarios.

Se apoya en `RepositorioCRUD` para crear/actualizar y solo añade consultas
especializadas como `obtener_por_username`.
"""
from sqlmodel import Session, select  # type: ignore

from app.base.repositorio import RepositorioCRUD
from app.modulos.usuarios.usuarios_modelo import Usuario


class RepositorioUsuario(RepositorioCRUD[Usuario]):
    modelo = Usuario
    campos_filtrables = {"usuario", "rol", "id"}
    campos_busqueda = {"nombres": "icontains", "correo": "icontains", "area": "icontains"}
    campos_actualizables = {"nombres", "correo", "rol", "area", "contrasena", "modificado_por"}
    orden_por_defecto = ("id", False)

    def __init__(self, db: Session):
        super().__init__(db)

    def obtener_por_username(self, *, username: str) -> Usuario | None:
        return self.db.exec(select(self.modelo).where(self.modelo.usuario == username)).first()
