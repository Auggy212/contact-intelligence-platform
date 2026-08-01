"""add suggestion and priority to clause_flags

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-06-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'clause_flags',
        sa.Column('suggestion', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        'clause_flags',
        sa.Column('priority', sa.String(16), nullable=True),
    )
    op.create_index(
        'ix_clause_flags_priority',
        'clause_flags',
        ['priority'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_clause_flags_priority', table_name='clause_flags')
    op.drop_column('clause_flags', 'priority')
    op.drop_column('clause_flags', 'suggestion')
