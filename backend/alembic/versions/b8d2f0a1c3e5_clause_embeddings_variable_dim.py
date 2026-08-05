"""make clause_embeddings.embedding variable-dimension

Revision ID: b8d2f0a1c3e5
Revises: a7c1e9d4b8f0
Create Date: 2026-08-03

The embedding column was fixed at vector(1024) (NVIDIA default). To let the
platform switch EMBEDDING_PROVIDER to a different-dimension model (e.g. local
bge = 384) WITHOUT a schema change each time, relax it to a variable-dimension
`vector` column. Qdrant remains the search index (per-dimension collections),
so this Postgres column is a provenance mirror only and needs no fixed dim.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "b8d2f0a1c3e5"
down_revision: Union[str, None] = "a7c1e9d4b8f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # vector(1024) -> vector  (drop the dimension constraint). Existing rows keep
    # their 1024-dim values; new rows may store any dimension.
    op.execute("ALTER TABLE clause_embeddings ALTER COLUMN embedding TYPE vector")


def downgrade() -> None:
    # Re-impose the 1024 dimension. Rows with a different dim would fail this cast;
    # acceptable for a downgrade (you'd re-embed with the 1024 provider first).
    op.execute("ALTER TABLE clause_embeddings ALTER COLUMN embedding TYPE vector(1024)")
