"""Log routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...memory import MemoryService
from ..deps import memory_dep

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
def list_logs(memory: MemoryService = Depends(memory_dep)) -> list[dict]:
    return [entry.model_dump(mode="json") for entry in memory.logs.list()]
