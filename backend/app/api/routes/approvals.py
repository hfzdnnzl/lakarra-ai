"""Approval queue routes: list, approve and reject."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...memory import MemoryService
from ...models.domain import ApprovalStatus
from ..deps import memory_dep

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("")
def list_approvals(memory: MemoryService = Depends(memory_dep)) -> list[dict]:
    return [a.model_dump(mode="json") for a in memory.approvals.list()]


def _decide(approval_id: str, status: ApprovalStatus, memory: MemoryService) -> dict:
    updated = memory.approvals.update(approval_id, status=status, decided_by="human")
    if updated is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return updated.model_dump(mode="json")


@router.post("/{approval_id}/approve")
def approve(approval_id: str, memory: MemoryService = Depends(memory_dep)) -> dict:
    return _decide(approval_id, ApprovalStatus.APPROVED, memory)


@router.post("/{approval_id}/reject")
def reject(approval_id: str, memory: MemoryService = Depends(memory_dep)) -> dict:
    return _decide(approval_id, ApprovalStatus.REJECTED, memory)
