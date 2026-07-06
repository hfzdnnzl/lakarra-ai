"""Analytics routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...memory import MemoryService
from ..deps import memory_dep

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("")
def list_analytics(memory: MemoryService = Depends(memory_dep)) -> list[dict]:
    return [a.model_dump(mode="json") for a in memory.analytics.list()]
