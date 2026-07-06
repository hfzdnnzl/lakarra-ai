"""Task routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...memory import MemoryService
from ...models.domain import Task
from ..deps import memory_dep

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
def list_tasks(memory: MemoryService = Depends(memory_dep)) -> list[dict]:
    return [t.model_dump(mode="json") for t in memory.tasks.list()]


@router.post("", status_code=201)
def create_task(task: Task, memory: MemoryService = Depends(memory_dep)) -> dict:
    return memory.tasks.add(task).model_dump(mode="json")


@router.get("/{task_id}")
def get_task(task_id: str, memory: MemoryService = Depends(memory_dep)) -> dict:
    task = memory.tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.model_dump(mode="json")
