"""add_law_citation_to_clause_flags

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-18 21:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clause_flags", sa.Column("law_act_name", sa.String(256), nullable=True))
    op.add_column("clause_flags", sa.Column("law_section_number", sa.String(64), nullable=True))
    op.add_column("clause_flags", sa.Column("law_retrieved_text", sa.Text(), nullable=True))
    op.add_column("clause_flags", sa.Column("law_jurisdiction", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("clause_flags", "law_jurisdiction")
    op.drop_column("clause_flags", "law_retrieved_text")
    op.drop_column("clause_flags", "law_section_number")
    op.drop_column("clause_flags", "law_act_name")
