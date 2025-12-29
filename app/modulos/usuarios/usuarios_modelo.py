"""
# Modelo SQLModel para usuarios del sistema.
#
# Se apoya en AuditMixin para no repetir campos de auditoría en cada tabla.
# Se usa el nombre de atributo Python `contrasena` (ASCII) pero se mapea a una
# columna con nombre "contraseña" para compatibilidad con bases existentes.
"""
from sqlalchemy import Column, String  # type: ignore
from sqlmodel import Field, SQLModel  # type: ignore

from app.base.auditoria import AuditMixin


class Usuario(AuditMixin, SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    usuario: str = Field(unique=True, index=True)
    # Atributo Python sin tilde; columna física con nombre "contraseña"
    contrasena: str = Field(sa_column=Column("contraseña", String))
    nombres: str
    rol: str = Field(default="funcionario")
    correo: str = Field(default="")
    area: str | None = None
