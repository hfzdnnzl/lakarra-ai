"""video_uploads table for analytics direct upload

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-07-09 13:10:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e7f8a9b0c1d2"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("video_uploads"):
        op.create_table(
            "video_uploads",
            sa.Column("id", sa.String(length=32), nullable=False),
            sa.Column("video_id", sa.String(length=128), nullable=False),
            sa.Column("tiktok_handle", sa.String(length=128), nullable=False),
            sa.Column("storage_key", sa.String(length=512), nullable=False),
            sa.Column("mime_type", sa.String(length=128), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("video_id"),
        )
        op.create_index("ix_video_uploads_video_id", "video_uploads", ["video_id"])
        op.create_index("ix_video_uploads_tiktok_handle", "video_uploads", ["tiktok_handle"])


def downgrade() -> None:
    op.drop_table("video_uploads")
