"""initial schema with pgvector, RLS, and all 16 tables

Revision ID: 0001
Revises:
Create Date: 2026-05-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── organizations ─────────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("clerk_org_id", sa.String(128), unique=True, nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("slug", sa.String(128), unique=True, nullable=False),
        sa.Column("logo_url", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_organizations_clerk_org_id", "organizations", ["clerk_org_id"])
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    # ── workspaces ────────────────────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_workspaces_organization_id", "workspaces", ["organization_id"])

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("clerk_user_id", sa.String(128), unique=True, nullable=False),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("full_name", sa.String(256), nullable=False),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── memberships ───────────────────────────────────────────────────────────
    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(32), server_default="viewer", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
    )

    # ── projects ──────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(32), server_default="draft", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"])

    # ── project_files ─────────────────────────────────────────────────────────
    op.create_table(
        "project_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_role", sa.String(4), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("parse_status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_project_files_project_id", "project_files", ["project_id"])
    op.create_index("ix_project_files_organization_id", "project_files", ["organization_id"])

    # ── parsed_clauses ────────────────────────────────────────────────────────
    op.create_table(
        "parsed_clauses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clause_number", sa.String(64), nullable=True),
        sa.Column("heading", sa.String(512), nullable=True),
        sa.Column("body_text", sa.Text, nullable=False),
        sa.Column("paragraph_index", sa.Integer, nullable=False),
        sa.Column("char_start", sa.Integer, nullable=False),
        sa.Column("char_end", sa.Integer, nullable=False),
        sa.Column("has_tracked_insertion", sa.Boolean, server_default="false"),
        sa.Column("has_tracked_deletion", sa.Boolean, server_default="false"),
        sa.Column("has_strikethrough", sa.Boolean, server_default="false"),
        sa.Column("has_comment", sa.Boolean, server_default="false"),
        sa.Column("change_metadata", postgresql.JSONB, nullable=True),
        sa.Column("embedding", postgresql.ARRAY(sa.Float), nullable=True),  # set via pgvector later
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_parsed_clauses_file_id", "parsed_clauses", ["file_id"])
    op.create_index("ix_parsed_clauses_project_id", "parsed_clauses", ["project_id"])
    op.create_index("ix_parsed_clauses_organization_id", "parsed_clauses", ["organization_id"])

    # Add pgvector column properly
    op.execute("ALTER TABLE parsed_clauses ADD COLUMN IF NOT EXISTS embedding vector(1024)")

    # ── analysis_tasks ────────────────────────────────────────────────────────
    op.create_table(
        "analysis_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), server_default="queued", nullable=False),
        sa.Column("celery_task_id", sa.String(256), nullable=True),
        sa.Column("model_version", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("input_file_ids", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_analysis_tasks_project_id", "analysis_tasks", ["project_id"])
    op.create_index("ix_analysis_tasks_organization_id", "analysis_tasks", ["organization_id"])

    # ── task_results ──────────────────────────────────────────────────────────
    op.create_table(
        "task_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_output", postgresql.JSONB, nullable=False),
        sa.Column("token_usage", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── clause_flags ──────────────────────────────────────────────────────────
    op.create_table(
        "clause_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("clause_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flag_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("recommendation", sa.Text, nullable=True),
        sa.Column("source_clause_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("reasoning_trace", sa.Text, nullable=True),
        sa.Column("reviewer_status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("reviewer_note", sa.Text, nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_clause_flags_project_id", "clause_flags", ["project_id"])
    op.create_index("ix_clause_flags_organization_id", "clause_flags", ["organization_id"])

    # ── clause_library_entries ────────────────────────────────────────────────
    op.create_table(
        "clause_library_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("added_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("body_text", sa.Text, nullable=False),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("tags", sa.String(512), nullable=True),
        sa.Column("status", sa.String(16), server_default="approved", nullable=False),
        sa.Column("qdrant_point_id", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_clause_library_entries_organization_id", "clause_library_entries", ["organization_id"])

    # ── checklist_rules ───────────────────────────────────────────────────────
    op.create_table(
        "checklist_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rule_code", sa.String(16), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("rule_config", postgresql.JSONB, nullable=False),
        sa.Column("is_enabled", sa.Boolean, server_default="true", nullable=False),
        sa.Column("is_default", sa.Boolean, server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_checklist_rules_organization_id", "checklist_rules", ["organization_id"])

    # ── subscriptions ─────────────────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("stripe_customer_id", sa.String(128), unique=True, nullable=True),
        sa.Column("stripe_subscription_id", sa.String(128), unique=True, nullable=True),
        sa.Column("plan", sa.String(32), server_default="trial", nullable=False),
        sa.Column("status", sa.String(32), server_default="trialing", nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── usage_records ─────────────────────────────────────────────────────────
    op.create_table(
        "usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("billing_period", sa.String(7), nullable=False),
        sa.Column("contracts_processed", sa.Integer, server_default="0", nullable=False),
        sa.Column("ai_tokens_used", sa.BigInteger, server_default="0", nullable=False),
        sa.Column("storage_bytes_used", sa.BigInteger, server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── audit_log ─────────────────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("model_version", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_log_organization_id", "audit_log", ["organization_id"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])

    # ── Row-Level Security on all tenant-scoped tables ─────────────────────────
    tenant_tables = [
        "workspaces", "projects", "project_files", "parsed_clauses",
        "analysis_tasks", "task_results", "clause_flags", "clause_library_entries",
        "checklist_rules", "subscriptions", "usage_records", "audit_log",
    ]
    for table in tenant_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (organization_id = current_setting('app.tenant_id', true)::uuid)
        """)

    # Allow superuser/migration role to bypass RLS
    op.execute("ALTER TABLE organizations DISABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    tables = [
        "audit_log", "usage_records", "subscriptions", "checklist_rules",
        "clause_library_entries", "clause_flags", "task_results", "analysis_tasks",
        "parsed_clauses", "project_files", "projects", "memberships",
        "users", "workspaces", "organizations",
    ]
    for table in tables:
        op.drop_table(table)
    op.execute("DROP EXTENSION IF EXISTS vector")
