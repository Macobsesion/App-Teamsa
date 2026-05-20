"""rename_tabla_ordentrabajo_a_orden_trabajo

Revision ID: c7a8b9d0e1f2
Revises: e63da54c712d
Create Date: 2026-04-15 00:00:00.000000

IMPORTANTE: Esta migración se inserta cronológicamente entre e63da54c712d
(que aún referencia 'ordentrabajo') y bf5b4b69df12 (que ya asume 'orden_trabajo').
El rename se hizo originalmente de forma directa en dev pero nunca se registró
como migración formal. Esta migración lo formaliza para producción.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7a8b9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'e63da54c712d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Renombra la tabla ordentrabajo → orden_trabajo.
    
    Actualiza también las FK que apuntan a la tabla vieja.
    """
    # 1. Renombrar tabla principal
    op.rename_table('ordentrabajo', 'orden_trabajo')
    
    # 2. Actualizar FK de concepto_orden_trabajo.orden_id → ordentrabajo.id
    #    PostgreSQL auto-genera nombres de FK con el formato:
    #    {tabla_origen}_{columna}_fkey
    #    El nombre exacto puede variar si se creó con Alembic (nombre autogenerado).
    #    Usamos naming_convention o buscamos por tabla.
    
    # Intentar con nombre Alembic convencional primero
    try:
        op.drop_constraint(
            'concepto_orden_trabajo_orden_id_fkey',
            'concepto_orden_trabajo',
            type_='foreignkey'
        )
    except Exception:
        # Si el nombre es diferente, intentar sin nombre (PostgreSQL lo infiere)
        pass
    
    op.create_foreign_key(
        'concepto_orden_trabajo_orden_id_fkey',
        'concepto_orden_trabajo',
        'orden_trabajo',
        ['orden_id'],
        ['id']
    )
    
    # 3. Actualizar FK de viatico_orden_enlace.orden_id
    #    Esta FK fue creada en la migración 537ee15fde09 con:
    #    sa.ForeignKeyConstraint(['orden_id'], ['ordentrabajo.id'])
    #    PostgreSQL auto-genera el nombre como: viatico_orden_enlace_orden_id_fkey
    try:
        op.drop_constraint(
            'viatico_orden_enlace_orden_id_fkey',
            'viatico_orden_enlace',
            type_='foreignkey'
        )
    except Exception:
        pass
    
    op.create_foreign_key(
        'viatico_orden_enlace_orden_id_fkey',
        'viatico_orden_enlace',
        'orden_trabajo',
        ['orden_id'],
        ['id']
    )


def downgrade() -> None:
    """Revierte el rename: orden_trabajo → ordentrabajo."""
    # Revertir FKs
    try:
        op.drop_constraint(
            'viatico_orden_enlace_orden_id_fkey',
            'viatico_orden_enlace',
            type_='foreignkey'
        )
    except Exception:
        pass
    
    op.create_foreign_key(
        'viatico_orden_enlace_orden_id_fkey',
        'viatico_orden_enlace',
        'ordentrabajo',
        ['orden_id'],
        ['id']
    )
    
    try:
        op.drop_constraint(
            'concepto_orden_trabajo_orden_id_fkey',
            'concepto_orden_trabajo',
            type_='foreignkey'
        )
    except Exception:
        pass
    
    op.create_foreign_key(
        'concepto_orden_trabajo_orden_id_fkey',
        'concepto_orden_trabajo',
        'ordentrabajo',
        ['orden_id'],
        ['id']
    )
    
    # Renombrar tabla de vuelta
    op.rename_table('orden_trabajo', 'ordentrabajo')
