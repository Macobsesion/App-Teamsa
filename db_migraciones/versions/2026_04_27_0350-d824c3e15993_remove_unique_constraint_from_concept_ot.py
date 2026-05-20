"""remove unique constraint from concept_ot

Revision ID: d824c3e15993
Revises: 2013841ebed6
Create Date: 2026-04-27 03:50:11.342061

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd824c3e15993'
down_revision: Union[str, Sequence[str], None] = '2013841ebed6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Eliminar índice único
    op.drop_index('ix_concepto_orden_trabajo_concepto_cotizacion_id', table_name='concepto_orden_trabajo')
    # Crear índice no único
    op.create_index('ix_concepto_orden_trabajo_concepto_cotizacion_id', 'concepto_orden_trabajo', ['concepto_cotizacion_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Eliminar índice no único
    op.drop_index('ix_concepto_orden_trabajo_concepto_cotizacion_id', table_name='concepto_orden_trabajo')
    # Crear índice único
    op.create_index('ix_concepto_orden_trabajo_concepto_cotizacion_id', 'concepto_orden_trabajo', ['concepto_cotizacion_id'], unique=True)
