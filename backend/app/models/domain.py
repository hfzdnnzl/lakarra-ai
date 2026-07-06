"""Domain models shared across the platform.

These Pydantic models define the *structured JSON contracts* that agents use to
communicate. Free-form text between agents is discouraged; agents exchange these
typed objects instead.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return uuid4().hex


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BaseRecord(BaseModel):
    """Common fields for every persisted record."""

    id: str = Field(default_factory=_new_id)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Task(BaseRecord):
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    assigned_agent: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Report(BaseRecord):
    agent: str
    title: str
    summary: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class ContentIdea(BaseRecord):
    title: str
    hook: str = ""
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    status: str = "draft"
    payload: dict[str, Any] = Field(default_factory=dict)


class Approval(BaseRecord):
    workflow: str
    subject: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by: str | None = None
    decided_by: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AnalyticsSnapshot(BaseRecord):
    metric: str
    value: float
    dimension: str | None = None


class LogEntry(BaseRecord):
    level: str = "info"
    source: str = "system"
    message: str = ""
    context: dict[str, Any] = Field(default_factory=dict)


class WorkflowRun(BaseRecord):
    workflow: str
    status: str = "completed"
    steps: list[dict[str, Any]] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
