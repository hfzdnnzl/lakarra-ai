"""add tiktok account snapshot columns

Revision ID: f60626417a25
Revises: f8a9b0c1d2e3
Create Date: 2026-07-12 01:10:49.490703
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = 'f60626417a25'
down_revision = 'f8a9b0c1d2e3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('analytics_account_settings', sa.Column('tiktok_snapshot', sa.JSON(), nullable=True))
    op.add_column('analytics_account_settings', sa.Column('tiktok_snapshot_fetched_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('analytics_account_settings', 'tiktok_snapshot_fetched_at')
    op.drop_column('analytics_account_settings', 'tiktok_snapshot')
