"""Shared API dependencies."""

from __future__ import annotations

from ..memory import MemoryService, get_memory


def memory_dep() -> MemoryService:
    return get_memory()
