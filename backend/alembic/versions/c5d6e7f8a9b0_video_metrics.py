"""video metrics table

Revision ID: c5d6e7f8a9b0
Revises: b4e5f6a7c8d9
Create Date: 2026-07-08 16:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "c5d6e7f8a9b0"
down_revision = "b4e5f6a7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("video_metrics"):
        op.create_table(
            "video_metrics",
            sa.Column("id", sa.String(length=32), nullable=False),
            sa.Column("video_id", sa.String(length=128), nullable=False),
            sa.Column("tiktok_handle", sa.String(length=128), nullable=False),
            sa.Column("views", sa.Integer(), nullable=True),
            sa.Column("likes", sa.Integer(), nullable=True),
            sa.Column("comments", sa.Integer(), nullable=True),
            sa.Column("shares", sa.Integer(), nullable=True),
            sa.Column("saves", sa.Integer(), nullable=True),
            sa.Column("reach", sa.Integer(), nullable=True),
            sa.Column("watch_time", sa.Float(), nullable=True),
            sa.Column("average_watch_duration", sa.Float(), nullable=True),
            sa.Column("completion_rate", sa.Float(), nullable=True),
            sa.Column("profile_visits", sa.Integer(), nullable=True),
            sa.Column("followers_gained", sa.Integer(), nullable=True),
            sa.Column("link_clicks", sa.Integer(), nullable=True),
            sa.Column("user_notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("video_id"),
        )
        op.create_index("ix_video_metrics_video_id", "video_metrics", ["video_id"])
        op.create_index("ix_video_metrics_tiktok_handle", "video_metrics", ["tiktok_handle"])


def downgrade() -> None:
    op.drop_table("video_metrics")
