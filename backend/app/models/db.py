"""SQLAlchemy ORM models (production persistence schema).

These mirror the domain models in :mod:`app.models.domain` and are the target for
the PostgreSQL memory backend and Alembic migrations. They are not used by the
default in-memory backend.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class TaskORM(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    assigned_agent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class ReportORM(TimestampMixin, Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    agent: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class ContentIdeaORM(TimestampMixin, Base):
    __tablename__ = "content_ideas"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    hook: Mapped[str] = mapped_column(Text, default="")
    caption: Mapped[str] = mapped_column(Text, default="")
    hashtags: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class ApprovalORM(TimestampMixin, Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    workflow: Mapped[str] = mapped_column(String(128))
    subject: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    requested_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class AnalyticsSnapshotORM(TimestampMixin, Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    metric: Mapped[str] = mapped_column(String(128))
    value: Mapped[float] = mapped_column(Float)
    dimension: Mapped[str | None] = mapped_column(String(128), nullable=True)


class LogEntryORM(TimestampMixin, Base):
    __tablename__ = "logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    level: Mapped[str] = mapped_column(String(16), default="info")
    source: Mapped[str] = mapped_column(String(64), default="system")
    message: Mapped[str] = mapped_column(Text, default="")
    context: Mapped[dict] = mapped_column(JSON, default=dict)


class WorkflowRunORM(TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    workflow: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="completed")
    steps: Mapped[list] = mapped_column(JSON, default=list)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
