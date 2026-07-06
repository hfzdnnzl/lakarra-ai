"""Memory abstraction.

The platform has a *shared memory* used by all agents plus a per-agent
*namespace* for private state. Concrete backends (in-memory, PostgreSQL) implement
these interfaces so business logic never depends on a specific storage engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Collection(ABC, Generic[T]):
    """A typed collection of domain records (e.g. tasks, reports)."""

    @abstractmethod
    def add(self, record: T) -> T: ...

    @abstractmethod
    def get(self, record_id: str) -> T | None: ...

    @abstractmethod
    def list(self) -> list[T]: ...

    @abstractmethod
    def update(self, record_id: str, **changes: Any) -> T | None: ...

    @abstractmethod
    def delete(self, record_id: str) -> bool: ...

    @abstractmethod
    def clear(self) -> None: ...


class KeyValueStore(ABC):
    """A private, per-agent namespace for scratch/working memory."""

    @abstractmethod
    def set(self, key: str, value: Any) -> None: ...

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any: ...

    @abstractmethod
    def all(self) -> dict[str, Any]: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class MemoryStore(ABC):
    """Entry point for all shared and per-agent memory access."""

    @abstractmethod
    def collection(self, name: str, model: type[T]) -> Collection[T]:
        """Return the shared collection identified by ``name``."""

    @abstractmethod
    def namespace(self, agent: str) -> KeyValueStore:
        """Return the private key/value namespace for ``agent``."""
