"""Report routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...memory import MemoryService
from ..deps import memory_dep

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
def list_reports(memory: MemoryService = Depends(memory_dep)) -> list[dict]:
    return [r.model_dump(mode="json") for r in memory.reports.list()]
