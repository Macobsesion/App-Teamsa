"""
# Esquemas Pydantic para datos de usuario.
#
# - Usa EmailStr para validar correos desde el backend.
# - Cambia "contraseña" a "contrasena" para mantener ASCII en el código.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator  # type: ignore

from app.base.tipos import RolUsuario, formatear_fecha


class UsuarioBase(BaseModel):
    usuario: str
    nombres: str
    rol: RolUsuario
    correo: EmailStr
    area: str


class UsuarioCreate(BaseModel):
    usuario: str
    nombres: str
    contrasena: str
    rol: RolUsuario | None = None
    correo: EmailStr


class UsuarioListado(UsuarioBase):
    pass


class UsuarioRead(UsuarioBase):
    id: int
    fecha_creacion: str
    fecha_modificacion: str | None = None
    creado_por: str
    modificado_por: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("fecha_creacion", "fecha_modificacion", mode="before")
    @classmethod
    def _formatear_fechas(cls, valor: datetime | None):
        return formatear_fecha(valor)


class UsuarioUpdatePartial(BaseModel):
    nombres: str | None = None
    correo: str | None = None
    area: str | None = None
    rol: RolUsuario | None = None
    contrasena: str | None = None

    @field_validator("contrasena", mode="before")
    @classmethod
    def _v_contrasena_vacia(cls, v):
        if v is None:
            return v
        try:
            s = str(v)
            return s if s.strip() else None
        except Exception:
            return None


class UsuarioIdentity(BaseModel):
    usuario: str
    rol: RolUsuario
