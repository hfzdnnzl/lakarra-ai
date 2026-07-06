"""High-level memory service.

Wraps a :class:`MemoryStore` and exposes typed accessors for the shared
collections described in the architecture (tasks, reports, generated content,
competitor research, analytics, conversation history, decisions, priorities).
"""

from __future__ import annotations

from ..models.domain import (
    AnalyticsSnapshot,
    Approval,
    ContentIdea,
    LogEntry,
    Report,
    Task,
    WorkflowRun,
)
from .base import Collection, KeyValueStore, MemoryStore


class MemoryService:
    """Facade over the raw :class:`MemoryStore`."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    # --- shared collections ------------------------------------------------
    @property
    def tasks(self) -> Collection[Task]:
        return self._store.collection("tasks", Task)

    @property
    def reports(self) -> Collection[Report]:
        return self._store.collection("reports", Report)

    @property
    def content(self) -> Collection[ContentIdea]:
        return self._store.collection("content", ContentIdea)

    @property
    def approvals(self) -> Collection[Approval]:
        return self._store.collection("approvals", Approval)

    @property
    def analytics(self) -> Collection[AnalyticsSnapshot]:
        return self._store.collection("analytics", AnalyticsSnapshot)

    @property
    def logs(self) -> Collection[LogEntry]:
        return self._store.collection("logs", LogEntry)

    @property
    def workflow_runs(self) -> Collection[WorkflowRun]:
        return self._store.collection("workflow_runs", WorkflowRun)

    # --- per-agent private memory -----------------------------------------
    def namespace(self, agent: str) -> KeyValueStore:
        """Return the private working-memory namespace for ``agent``."""

        return self._store.namespace(agent)
