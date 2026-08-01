"""add clause_type and value_changes to clause_flags

Revision ID: e1f2a3b4c5d6
Revises: dd7e3d60e666
Create Date: 2026-06-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e1f2a3b4c5d6'
down_revision = 'dd7e3d60e666'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'clause_flags',
        sa.Column('clause_type', sa.String(64), nullable=True),
    )
    op.add_column(
        'clause_flags',
        sa.Column('value_changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index(
        'ix_clause_flags_clause_type',
        'clause_flags',
        ['clause_type'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_clause_flags_clause_type', table_name='clause_flags')
    op.drop_column('clause_flags', 'value_changes')
    op.drop_column('clause_flags', 'clause_type')
