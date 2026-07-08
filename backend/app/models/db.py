"""SQLAlchemy ORM models (production persistence schema).

These mirror the domain models in :mod:`app.models.domain` and are the target for
the PostgreSQL memory backend and Alembic migrations. They are not used by the
default in-memory backend.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


# ---------------------------------------------------------------------------
# Content Management System (Phase 2.5)
# ---------------------------------------------------------------------------


class Content(TimestampMixin, Base):
    """A logical content item; holds the fields of its active version."""

    __tablename__ = "contents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(48), index=True)
    business_goal: Mapped[str] = mapped_column(Text, default="")
    target_audience: Mapped[str] = mapped_column(String(255), default="")
    product: Mapped[str] = mapped_column(String(255), default="")
    hook: Mapped[str] = mapped_column(Text, default="")
    duration: Mapped[int] = mapped_column(Integer, default=15)
    caption: Mapped[str] = mapped_column(Text, default="")
    hashtags: Mapped[list] = mapped_column(JSON, default=list)
    cta: Mapped[str] = mapped_column(Text, default="")
    posting_time: Mapped[str] = mapped_column(String(128), default="")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    music_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    active_version: Mapped[int] = mapped_column(Integer, default=1)
    constraints: Mapped[list] = mapped_column(JSON, default=list)
    performance_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    scenes: Mapped[list[ContentScene]] = relationship(
        back_populates="content",
        cascade="all, delete-orphan",
        order_by="ContentScene.sequence_number",
    )
    versions: Mapped[list[ContentVersion]] = relationship(
        back_populates="content",
        cascade="all, delete-orphan",
        order_by="ContentVersion.version_number",
    )
    assets: Mapped[list[ContentAsset]] = relationship(
        back_populates="content",
        cascade="all, delete-orphan",
        order_by="ContentAsset.created_at",
    )
    reviews: Mapped[list[ContentReview]] = relationship(
        back_populates="content",
        cascade="all, delete-orphan",
        order_by="ContentReview.created_at",
    )


class ContentScene(Base):
    """A single persisted timeline scene (the storyboard breakdown)."""

    __tablename__ = "content_scenes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), index=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[int] = mapped_column(Integer)
    end_time: Mapped[int] = mapped_column(Integer)
    scene_description: Mapped[str] = mapped_column(Text, default="")
    camera_direction: Mapped[str] = mapped_column(String(255), default="")
    on_screen_text: Mapped[str] = mapped_column(Text, default="")
    voiceover: Mapped[str | None] = mapped_column(Text, nullable=True)
    sound_effect: Mapped[str | None] = mapped_column(String(255), nullable=True)

    content: Mapped[Content] = relationship(back_populates="scenes")


class ContentVersion(Base):
    """A point-in-time snapshot of a generated content plan."""

    __tablename__ = "content_versions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    hook: Mapped[str] = mapped_column(Text, default="")
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    content: Mapped[Content] = relationship(back_populates="versions")


class ContentStatusHistory(Base):
    """Records every status transition for a content item."""

    __tablename__ = "content_status_history"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), index=True
    )
    old_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32))
    changed_by: Mapped[str] = mapped_column(String(64), default="system")
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class ContentFeedback(Base):
    """Free-text user feedback stored for future Content Analyst use."""

    __tablename__ = "content_feedback"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), index=True
    )
    message: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(64), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ContentAsset(Base):
    """Uploaded media (e.g. filmed video) attached to a content item."""

    __tablename__ = "content_assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128))
    file_size: Mapped[int] = mapped_column(Integer)
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    content: Mapped[Content] = relationship(back_populates="assets")


class ContentReview(Base):
    """Agent review of uploaded content (fidelity or performance)."""

    __tablename__ = "content_reviews"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True
    )
    review_type: Mapped[str] = mapped_column(String(32))
    agent: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    content: Mapped[Content] = relationship(back_populates="reviews")


class ContentGeneration(Base):
    """Metadata about a single AI generation (for debugging/optimization)."""

    __tablename__ = "content_generations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), index=True
    )
    model_used: Mapped[str] = mapped_column(String(128), default="")
    prompt_version: Mapped[str] = mapped_column(String(128), default="")
    temperature: Mapped[float] = mapped_column(Float, default=0.0)
    token_usage: Mapped[dict] = mapped_column(JSON, default=dict)
    generation_time: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
