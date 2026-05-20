"""
# Esquemas Pydantic para datos de usuario.
#
# - Usa EmailStr para validar correos desde el backend.
# - Cambia "contraseña" a "contrasena" para mantener ASCII en el código.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator  # type: ignore
from sqlmodel import SQLModel, Field  # type: ignore
from sqlalchemy import Column, JSON

from app.base.tipos import RolUsuario, formatear_fecha



class UsuarioBase(SQLModel):
    usuario: str = Field(unique=True, index=True)
    nombres: str
    rol: str = Field(default="funcionario")
    # correo is EmailStr in Pydantic, but allowing empty string requires attention.
    # we use str for SQLModel wide-type, and Pydantic will validate on Create/Update
    correo: str = Field(default="")  
    area: str | None = None
    permisos_ver: list = Field(default_factory=list, sa_column=Column(JSON))
    permisos_crear: list = Field(default_factory=list, sa_column=Column(JSON))
    permisos_editar: list = Field(default_factory=list, sa_column=Column(JSON))
    permisos_eliminar: list = Field(default_factory=list, sa_column=Column(JSON))


class UsuarioCreate(BaseModel):
    usuario: str
    nombres: str
    contrasena: str
    rol: RolUsuario | None = None
    correo: EmailStr
    area: str | None = None


class UsuarioListado(UsuarioBase):
    pass


class UsuarioRead(UsuarioBase):
    id: int
    fecha_creacion: str
    fecha_modificacion: str | None = None
    creado_por: str
    modificado_por: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("fecha_creacion", "fecha_modificacion", mode="before", check_fields=False)
    @classmethod
    def _formatear_fechas(cls, valor: datetime | None):
        return formatear_fecha(valor)


class UsuarioUpdatePartial(BaseModel):
    nombres: str | None = None
    correo: str | None = None
    area: str | None = None
    rol: RolUsuario | None = None
    contrasena: str | None = None
    permisos_ver: list[str] | None = None
    permisos_crear: list[str] | None = None
    permisos_editar: list[str] | None = None
    permisos_eliminar: list[str] | None = None

class UsuarioUpdatePassword(BaseModel):
    contrasena: str
    confirmarContrasena: str | None = None

    @field_validator("contrasena", mode="before", check_fields=False)
    @classmethod
    def _v_contrasena_vacia(cls, v):
        if not v or not str(v).strip():
            raise ValueError("La contraseña no puede estar vacía")
        return str(v).strip()




class UsuarioIdentity(BaseModel):
    usuario: str
    rol: RolUsuario
