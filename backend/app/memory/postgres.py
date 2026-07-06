"""PostgreSQL-backed memory store (Phase 2 target).

This is a structural placeholder for the production persistence layer. The
SQLAlchemy models live in :mod:`app.models.db` and the session factory in
:mod:`app.database`. Implement the methods below to map domain records onto the
ORM models. Until then the platform defaults to the in-memory backend.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from .base import Collection, KeyValueStore, MemoryStore

T = TypeVar("T", bound=BaseModel)


class PostgresStore(MemoryStore):
    """Not yet implemented. See module docstring."""

    def collection(self, name: str, model: type[T]) -> Collection[T]:  # noqa: D102
        raise NotImplementedError(
            "PostgresStore is a Phase 2 placeholder. Set MEMORY_BACKEND=in_memory "
            "for development, or implement this backend against app.models.db."
        )

    def namespace(self, agent: str) -> KeyValueStore:  # noqa: D102
        raise NotImplementedError(
            "PostgresStore is a Phase 2 placeholder. Set MEMORY_BACKEND=in_memory "
            "for development, or implement this backend against app.models.db."
        )
