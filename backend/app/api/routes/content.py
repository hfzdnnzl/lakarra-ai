"""Content idea routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...memory import MemoryService
from ..deps import memory_dep

router = APIRouter(prefix="/content", tags=["content"])


@router.get("")
def list_content(memory: MemoryService = Depends(memory_dep)) -> list[dict]:
    return [c.model_dump(mode="json") for c in memory.content.list()]
