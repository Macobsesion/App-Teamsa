"""update_enum_cotizacion_enviada_a_emitida

Revision ID: d8b9c0e1f2a3
Revises: c7a8b9d0e1f2
Create Date: 2026-05-20 07:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8b9c0e1f2a3'
down_revision: Union[str, Sequence[str], None] = '567193e68bcd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Actualiza el valor del enum EstadoCotizacion de 'enviada' a 'emitida'.
    
    Cambio intencional de nomenclatura:
    - 'enviada' era ambiguo (¿enviada al cliente? ¿enviada por correo?)
    - 'emitida' es el término correcto del dominio (cotización emitida formalmente)
    
    Este UPDATE es seguro porque solo modifica un valor de texto en una columna VARCHAR,
    no cambia tipos de dato ni estructura.
    """
    op.execute(
        "UPDATE cotizaciones SET estado = 'emitida' WHERE estado = 'enviada'"
    )


def downgrade() -> None:
    """Revierte: 'emitida' → 'enviada'."""
    op.execute(
        "UPDATE cotizaciones SET estado = 'enviada' WHERE estado = 'emitida'"
    )
