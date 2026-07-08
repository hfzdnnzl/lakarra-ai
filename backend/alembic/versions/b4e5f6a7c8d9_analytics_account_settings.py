"""analytics account settings

Revision ID: b4e5f6a7c8d9
Revises: a3f1c2d4e5b6
Create Date: 2026-07-08 13:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b4e5f6a7c8d9"
down_revision = "a3f1c2d4e5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("analytics_account_settings"):
        op.create_table(
            "analytics_account_settings",
            sa.Column("id", sa.String(length=32), nullable=False),
            sa.Column("tiktok_handle", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("analytics_account_settings")
