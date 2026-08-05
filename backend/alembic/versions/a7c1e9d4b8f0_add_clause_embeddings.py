"""add clause_embeddings (chunk-level RAG index) and merge migration heads

Revision ID: a7c1e9d4b8f0
Revises: c3d4e5f6a7b8, f2a3b4c5d6e7
Create Date: 2026-08-02

Two things at once:
  1. Merges the two divergent heads that both branched off dd7e3d60e666
     (clause_flags risk/law/trial branch  +  clause_type/suggestion branch)
     back into a single linear head.
  2. Adds the clause_embeddings table: chunk-level vectors for semantic search /
     RAG (Phase 6), with tenant-isolation RLS matching every other tenant table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

from app.core.constants import CHUNK_EMBEDDING_DIMENSIONS

revision: str = "a7c1e9d4b8f0"
# Tuple down_revision = merge both heads into one.
down_revision: Union[str, Sequence[str], None] = ("c3d4e5f6a7b8", "f2a3b4c5d6e7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clause_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clause_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", sa.String(length=128), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("clause_type", sa.String(length=64), nullable=True),
        sa.Column("file_role", sa.String(length=8), nullable=True),
        sa.Column("embedding", Vector(CHUNK_EMBEDDING_DIMENSIONS), nullable=True),
        sa.Column("embedding_provider", sa.String(length=32), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clause_id"], ["parsed_clauses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clause_embeddings_organization_id", "clause_embeddings",
                    ["organization_id"])
    op.create_index("ix_clause_embeddings_project_id", "clause_embeddings", ["project_id"])
    op.create_index("ix_clause_embeddings_clause_id", "clause_embeddings", ["clause_id"])
    op.create_index("ix_clause_embeddings_document_id", "clause_embeddings", ["document_id"])
    op.create_index("ix_clause_embeddings_chunk_id", "clause_embeddings",
                    ["chunk_id"], unique=True)

    # Tenant-isolation RLS, identical policy to every other tenant-scoped table.
    op.execute("ALTER TABLE clause_embeddings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE clause_embeddings FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON clause_embeddings
        USING (organization_id = current_setting('app.tenant_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON clause_embeddings")
    op.drop_index("ix_clause_embeddings_chunk_id", table_name="clause_embeddings")
    op.drop_index("ix_clause_embeddings_document_id", table_name="clause_embeddings")
    op.drop_index("ix_clause_embeddings_clause_id", table_name="clause_embeddings")
    op.drop_index("ix_clause_embeddings_project_id", table_name="clause_embeddings")
    op.drop_index("ix_clause_embeddings_organization_id", table_name="clause_embeddings")
    op.drop_table("clause_embeddings")
