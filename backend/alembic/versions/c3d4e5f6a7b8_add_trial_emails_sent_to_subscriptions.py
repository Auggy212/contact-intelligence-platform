"""add_trial_lifecycle_columns

Adds trial_emails_sent bitmask to subscriptions and admin_email to organizations
to support the Celery Beat trial lifecycle email scheduler.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-18 22:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("trial_emails_sent", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "organizations",
        sa.Column("admin_email", sa.String(256), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "trial_emails_sent")
    op.drop_column("organizations", "admin_email")
