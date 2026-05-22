"""add_risk_score_to_clause_flags

Revision ID: a1b2c3d4e5f6
Revises: dd7e3d60e666
Create Date: 2026-05-18 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'dd7e3d60e666'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'clause_flags',
        sa.Column('risk_score', sa.Integer(), nullable=True),
    )
    op.create_index('ix_clause_flags_risk_score', 'clause_flags', ['risk_score'])


def downgrade() -> None:
    op.drop_index('ix_clause_flags_risk_score', table_name='clause_flags')
    op.drop_column('clause_flags', 'risk_score')
