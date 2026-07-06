"""In-memory implementation of the memory abstraction.

This is the default Phase 1 backend: it keeps all state in process, requiring no
database. It is intentionally simple and is safe for local development, demos and
tests. Swap in the PostgreSQL backend for production persistence.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any, TypeVar

from pydantic import BaseModel

from .base import Collection, KeyValueStore, MemoryStore

T = TypeVar("T", bound=BaseModel)


class InMemoryCollection(Collection[T]):
    def __init__(self, model: type[T]) -> None:
        self._model = model
        self._items: dict[str, T] = {}
        self._lock = threading.RLock()

    def add(self, record: T) -> T:
        with self._lock:
            self._items[record.id] = record  # type: ignore[attr-defined]
        return record

    def get(self, record_id: str) -> T | None:
        return self._items.get(record_id)

    def list(self) -> list[T]:
        return list(self._items.values())

    def update(self, record_id: str, **changes: Any) -> T | None:
        with self._lock:
            record = self._items.get(record_id)
            if record is None:
                return None
            data = record.model_dump()
            data.update(changes)
            data["updated_at"] = datetime.now(UTC)
            updated = self._model(**data)
            self._items[record_id] = updated
            return updated

    def delete(self, record_id: str) -> bool:
        with self._lock:
            return self._items.pop(record_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class InMemoryKeyValueStore(KeyValueStore):
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._lock = threading.RLock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def all(self) -> dict[str, Any]:
        return dict(self._data)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)


class InMemoryStore(MemoryStore):
    def __init__(self) -> None:
        self._collections: dict[str, InMemoryCollection[Any]] = {}
        self._namespaces: dict[str, InMemoryKeyValueStore] = {}
        self._lock = threading.RLock()

    def collection(self, name: str, model: type[T]) -> Collection[T]:
        with self._lock:
            if name not in self._collections:
                self._collections[name] = InMemoryCollection(model)
            return self._collections[name]

    def namespace(self, agent: str) -> KeyValueStore:
        with self._lock:
            if agent not in self._namespaces:
                self._namespaces[agent] = InMemoryKeyValueStore()
            return self._namespaces[agent]
