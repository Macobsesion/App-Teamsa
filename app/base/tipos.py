# Tipos compartidos para esquemas Pydantic.
from datetime import datetime
from typing import Literal

# Enumeraciones simples expresadas como Literal para mantener validaciones tipadas.
RolUsuario = Literal["admin", "funcionario", "productor", "conductor", "camarografo"]
TipoPrograma = Literal["grabado", "en_vivo"]
TipoInvitado = Literal["invitado", "testimonio"]
EstadoReservacion = Literal["pendiente", "confirmada", "cancelada"]


def formatear_fecha(valor: datetime | None) -> str | None:
    # Devuelve la fecha en formato YYYY-MM-DD HH:MM:SS o None.
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    return valor
