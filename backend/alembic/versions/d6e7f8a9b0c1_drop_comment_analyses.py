"""drop unused comment_analyses table

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-07-09 15:30:00.000000
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
    if inspector.has_table("comment_analyses"):
        op.drop_index("ix_comment_analyses_video_id", table_name="comment_analyses")
        op.drop_table("comment_analyses")


def downgrade() -> None:
    op.create_table(
        "comment_analyses",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("video_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("agent", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comment_analyses_video_id", "comment_analyses", ["video_id"])
