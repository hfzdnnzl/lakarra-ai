"""Add publish date/time overrides to video_metrics

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-07-09 14:20:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "f8a9b0c1d2e3"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("video_metrics"):
        columns = {col["name"] for col in inspector.get_columns("video_metrics")}
        if "publish_date" not in columns:
            op.add_column("video_metrics", sa.Column("publish_date", sa.String(length=32), nullable=True))
        if "publish_time" not in columns:
            op.add_column("video_metrics", sa.Column("publish_time", sa.String(length=16), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("video_metrics"):
        columns = {col["name"] for col in inspector.get_columns("video_metrics")}
        if "publish_time" in columns:
            op.drop_column("video_metrics", "publish_time")
        if "publish_date" in columns:
            op.drop_column("video_metrics", "publish_date")
