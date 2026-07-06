"""Memory layer package.

Provides a process-wide :class:`MemoryService` selected from configuration. The
default backend is in-memory (no external dependencies); ``postgres`` can be
enabled once a database is available.
"""

from __future__ import annotations

from functools import lru_cache

from ..config import get_settings
from .base import Collection, KeyValueStore, MemoryStore
from .in_memory import InMemoryStore
from .service import MemoryService

__all__ = [
    "Collection",
    "KeyValueStore",
    "MemoryStore",
    "MemoryService",
    "build_memory_store",
    "get_memory",
]


def build_memory_store() -> MemoryStore:
    """Instantiate the configured memory backend."""

    backend = get_settings().memory_backend
    if backend == "in_memory":
        return InMemoryStore()
    if backend == "postgres":
        # Imported lazily so the app boots without database drivers configured.
        from .postgres import PostgresStore

        return PostgresStore()
    raise ValueError(f"Unknown memory backend: {backend}")


@lru_cache
def get_memory() -> MemoryService:
    """Return the process-wide memory service (cached singleton)."""

    return MemoryService(build_memory_store())
