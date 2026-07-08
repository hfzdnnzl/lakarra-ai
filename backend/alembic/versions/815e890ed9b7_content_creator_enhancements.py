"""content creator enhancements

Revision ID: 815e890ed9b7
Revises: 50479057a779
Create Date: 2026-07-08 08:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "815e890ed9b7"
down_revision = "50479057a779"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    content_columns = {col["name"] for col in inspector.get_columns("contents")}
    if "constraints" not in content_columns:
        op.add_column(
            "contents",
            sa.Column("constraints", sa.JSON(), nullable=False, server_default="[]"),
        )
    if "performance_notes" not in content_columns:
        op.add_column("contents", sa.Column("performance_notes", sa.Text(), nullable=True))

    if not inspector.has_table("content_assets"):
        op.create_table(
            "content_assets",
            sa.Column("id", sa.String(length=32), nullable=False),
            sa.Column("content_id", sa.String(length=32), nullable=False),
            sa.Column("storage_key", sa.String(length=512), nullable=False),
            sa.Column("mime_type", sa.String(length=128), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["content_id"], ["contents.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_content_assets_content_id"), "content_assets", ["content_id"], unique=False
        )

    if not inspector.has_table("content_reviews"):
        op.create_table(
            "content_reviews",
            sa.Column("id", sa.String(length=32), nullable=False),
            sa.Column("content_id", sa.String(length=32), nullable=False),
            sa.Column("asset_id", sa.String(length=32), nullable=True),
            sa.Column("review_type", sa.String(length=32), nullable=False),
            sa.Column("agent", sa.String(length=64), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["content_id"], ["contents.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["asset_id"], ["content_assets.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_content_reviews_content_id"), "content_reviews", ["content_id"], unique=False
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_content_reviews_content_id"), table_name="content_reviews")
    op.drop_table("content_reviews")
    op.drop_index(op.f("ix_content_assets_content_id"), table_name="content_assets")
    op.drop_table("content_assets")
    op.drop_column("contents", "performance_notes")
    op.drop_column("contents", "constraints")
