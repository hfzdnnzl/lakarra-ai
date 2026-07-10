"""content tiktok_video_id link column

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-07-09 12:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d6e7f8a9b0c1"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("contents")}
    if "tiktok_video_id" not in columns:
        with op.batch_alter_table("contents") as batch_op:
            batch_op.add_column(sa.Column("tiktok_video_id", sa.String(length=128), nullable=True))
            batch_op.create_index("ix_contents_tiktok_video_id", ["tiktok_video_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("contents")}
    if "tiktok_video_id" in columns:
        with op.batch_alter_table("contents") as batch_op:
            batch_op.drop_index("ix_contents_tiktok_video_id")
            batch_op.drop_column("tiktok_video_id")
