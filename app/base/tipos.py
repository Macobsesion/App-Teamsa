# Tipos compartidos para esquemas Pydantic.
from datetime import datetime
from typing import Literal

# Roles activos del sistema TEAMSA.
RolUsuario = Literal["admin", "funcionario", "tecnico"]


def formatear_fecha(valor: datetime | None) -> str | None:
    # Devuelve la fecha en formato YYYY-MM-DD HH:MM:SS o None.
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    return valor
