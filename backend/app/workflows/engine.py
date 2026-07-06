"""LangGraph workflow engine (Phase 1 skeleton).

Compiles a :class:`WorkflowDefinition` into a LangGraph ``StateGraph`` with:

* **Agent routing** -- one node per step, wired sequentially.
* **State management** -- a shared :class:`WorkflowState`.
* **Checkpoints** -- a ``MemorySaver`` so runs can be paused/resumed.
* **Human approval** -- an ``interrupt_before`` gate node when required.
* **Retries** -- per-node retry loop around agent execution.

The routing here is intentionally simple (sequential); the structure supports
richer conditional routing without changing agents or the API.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ..agents import AgentContext, AgentRequest, registry
from ..models.domain import Approval
from .definitions import WorkflowDefinition, WorkflowStep
from .state import WorkflowState

# A process-wide checkpointer so a workflow paused for approval can be resumed by
# a *different* engine instance (e.g. across separate API requests) using the same
# thread id. Swap for a persistent checkpointer (Postgres/Redis) in Phase 2.
_SHARED_CHECKPOINTER = MemorySaver()


class WorkflowEngine:
    """Builds and runs a single workflow definition."""

    def __init__(self, definition: WorkflowDefinition, context: AgentContext) -> None:
        self.definition = definition
        self.context = context
        self.checkpointer = _SHARED_CHECKPOINTER
        self._compiled = self._build()

    # --- graph construction ------------------------------------------------
    def _node_id(self, index: int, step: WorkflowStep) -> str:
        return f"{index:02d}_{step.agent}"

    def _make_agent_node(self, step: WorkflowStep) -> Callable[[WorkflowState], dict[str, Any]]:
        def node(state: WorkflowState) -> dict[str, Any]:
            agent = registry.instantiate(step.agent, self.context)
            if agent is None:
                raise ValueError(f"Unknown agent: {step.agent}")

            request = AgentRequest(
                workflow=self.definition.name,
                payload={**state.get("payload", {}), "results": state.get("results", {})},
            )

            last_error: Exception | None = None
            for _ in range(max(1, step.retries)):
                try:
                    result = agent.handle(request)
                    results = dict(state.get("results", {}))
                    results[step.agent] = result.output
                    step_entry = {
                        "agent": step.agent,
                        "status": result.status,
                        "output": result.output,
                    }
                    return {"results": results, "steps": [step_entry]}
                except Exception as exc:  # noqa: BLE001 - retried below
                    last_error = exc
            raise RuntimeError(f"Agent {step.agent} failed after retries: {last_error}")

        return node

    def _request_approval_node(self, state: WorkflowState) -> dict[str, Any]:
        # Runs *before* the interrupt: record a pending approval so it surfaces in
        # the Approval Queue while the workflow is paused.
        self.context.memory.approvals.add(
            Approval(
                workflow=self.definition.name,
                subject=f"Approve output of workflow '{self.definition.name}'",
                requested_by="workflow_engine",
                payload={"results": state.get("results", {})},
            )
        )
        return {"status": "awaiting_approval"}

    def _finalize_node(self, state: WorkflowState) -> dict[str, Any]:
        # Runs only after a human resumes the paused workflow.
        return {"status": "completed"}

    def _build(self):
        graph: StateGraph = StateGraph(WorkflowState)

        previous = START
        for index, step in enumerate(self.definition.steps):
            node_id = self._node_id(index, step)
            graph.add_node(node_id, self._make_agent_node(step))
            graph.add_edge(previous, node_id)
            previous = node_id

        interrupt_before: list[str] = []
        if self.definition.requires_approval:
            # request_approval runs, then the graph pauses before finalize until a
            # human approves and the run is resumed.
            graph.add_node("request_approval", self._request_approval_node)
            graph.add_node("finalize", self._finalize_node)
            graph.add_edge(previous, "request_approval")
            graph.add_edge("request_approval", "finalize")
            graph.add_edge("finalize", END)
            interrupt_before = ["finalize"]
        else:
            graph.add_edge(previous, END)

        return graph.compile(checkpointer=self.checkpointer, interrupt_before=interrupt_before)

    # --- execution ---------------------------------------------------------
    def run(
        self, payload: dict[str, Any] | None = None, *, thread_id: str = "default"
    ) -> WorkflowState:
        """Run the workflow. If an approval gate is hit, the run pauses there."""

        config = {"configurable": {"thread_id": thread_id}}
        initial: WorkflowState = {
            "workflow": self.definition.name,
            "payload": payload or {},
            "results": {},
            "steps": [],
            "status": "running",
        }
        self._compiled.invoke(initial, config=config)
        return self.snapshot(thread_id=thread_id)

    def resume(self, *, thread_id: str = "default") -> WorkflowState:
        """Resume a run that paused at the human-approval gate."""

        config = {"configurable": {"thread_id": thread_id}}
        self._compiled.invoke(None, config=config)
        return self.snapshot(thread_id=thread_id)

    def snapshot(self, *, thread_id: str = "default") -> WorkflowState:
        config = {"configurable": {"thread_id": thread_id}}
        state = self._compiled.get_state(config)
        values: WorkflowState = dict(state.values)  # type: ignore[assignment]
        # If there are pending nodes we are paused (e.g. awaiting approval).
        values["status"] = "awaiting_approval" if state.next else "completed"
        return values
