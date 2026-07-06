"""Workflow routes: list definitions, run/resume, and view run history."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...agents import get_agent_context
from ...memory import MemoryService
from ...scheduler import scheduler
from ...workflows import registry as workflow_registry
from ...workflows import run_workflow
from ...workflows.engine import WorkflowEngine
from ..deps import memory_dep

router = APIRouter(prefix="/workflows", tags=["workflows"])


class RunPayload(BaseModel):
    payload: dict = {}
    thread_id: str = "default"


@router.get("")
def list_workflows() -> list[dict]:
    return [
        {
            "name": d.name,
            "description": d.description,
            "steps": [s.agent for s in d.steps],
            "requires_approval": d.requires_approval,
        }
        for d in workflow_registry.all()
    ]


@router.get("/schedule")
def list_schedule() -> list[dict]:
    return [
        {"name": j.name, "workflow": j.workflow, "schedule": j.schedule, "enabled": j.enabled}
        for j in scheduler.jobs()
    ]


@router.get("/history")
def workflow_history(memory: MemoryService = Depends(memory_dep)) -> list[dict]:
    return [r.model_dump(mode="json") for r in memory.workflow_runs.list()]


@router.post("/{name}/run")
def run(name: str, body: RunPayload) -> dict:
    if workflow_registry.get(name) is None:
        raise HTTPException(status_code=404, detail=f"Unknown workflow: {name}")
    state = run_workflow(name, body.payload, thread_id=body.thread_id)
    return dict(state)


@router.post("/{name}/resume")
def resume(name: str, body: RunPayload) -> dict:
    definition = workflow_registry.get(name)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Unknown workflow: {name}")
    engine = WorkflowEngine(definition, get_agent_context())
    return dict(engine.resume(thread_id=body.thread_id))
