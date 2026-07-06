"""Workflow registry and runner service."""

from __future__ import annotations

from ..agents import get_agent_context
from ..memory import get_memory
from ..models.domain import WorkflowRun
from .definitions import CONTENT_PIPELINE, DAILY_PRIORITIES, WorkflowDefinition
from .engine import WorkflowEngine
from .state import WorkflowState


class WorkflowRegistry:
    def __init__(self) -> None:
        self._defs: dict[str, WorkflowDefinition] = {}

    def register(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        self._defs[definition.name] = definition
        return definition

    def get(self, name: str) -> WorkflowDefinition | None:
        return self._defs.get(name)

    def names(self) -> list[str]:
        return sorted(self._defs)

    def all(self) -> list[WorkflowDefinition]:
        return list(self._defs.values())


#: Process-wide workflow registry, seeded with the example definitions.
registry = WorkflowRegistry()
registry.register(DAILY_PRIORITIES)
registry.register(CONTENT_PIPELINE)


def run_workflow(
    name: str, payload: dict | None = None, *, thread_id: str = "default"
) -> WorkflowState:
    """Run a registered workflow by name and persist a :class:`WorkflowRun`."""

    definition = registry.get(name)
    if definition is None:
        raise ValueError(f"Unknown workflow: {name}")

    engine = WorkflowEngine(definition, get_agent_context())
    state = engine.run(payload, thread_id=thread_id)

    get_memory().workflow_runs.add(
        WorkflowRun(
            workflow=name,
            status=state.get("status", "completed"),
            steps=state.get("steps", []),
            result=state.get("results", {}),
        )
    )
    return state
