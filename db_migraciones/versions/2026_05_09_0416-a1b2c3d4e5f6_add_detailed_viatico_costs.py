"""add detailed viatico costs

Revision ID: a1b2c3d4e5f6
Revises: d824c3e15993
Create Date: 2026-05-09 04:16:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from decimal import Decimal


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd824c3e15993'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('viaticos', sa.Column('costo_peajes', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'))
    op.add_column('viaticos', sa.Column('costo_estacionamiento', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('viaticos', 'costo_peajes')
    op.drop_column('viaticos', 'costo_estacionamiento')
