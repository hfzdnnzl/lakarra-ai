"""CEO Agent (Phase 1 mock).

Responsibilities: prioritize work, allocate resources, decide which workflows run
and monitor overall business health.
"""

from __future__ import annotations

from ...models.domain import Priority, Report, Task
from ..base import AgentRequest, AgentResult, BaseAgent
from ..registry import register_agent


@register_agent
class CEOAgent(BaseAgent):
    name = "ceo"
    role = "CEO"
    description = "Prioritizes work, allocates resources and monitors business health."

    def handle(self, request: AgentRequest) -> AgentResult:
        memory = self.context.memory

        # Mock prioritization output.
        priorities = [
            {"item": "Grow TikTok reach", "priority": Priority.HIGH.value},
            {"item": "Launch wedding card campaign", "priority": Priority.MEDIUM.value},
            {"item": "Research competitors", "priority": Priority.MEDIUM.value},
        ]
        assignments = [
            {"agent": "marketing_manager", "task": "Draft weekly content strategy"},
            {"agent": "product_research", "task": "Competitor gap analysis"},
        ]

        # Persist an assigned task and a report into shared memory.
        task = memory.tasks.add(
            Task(
                title="Draft weekly content strategy",
                priority=Priority.HIGH,
                assigned_agent="marketing_manager",
            )
        )
        memory.reports.add(
            Report(
                agent=self.name,
                title="Daily priorities",
                summary="Mock daily prioritization output.",
                payload={"priorities": priorities, "assignments": assignments},
            )
        )

        return AgentResult(
            agent=self.name,
            output={
                "priorities": priorities,
                "assignments": assignments,
                "resource_allocation": {"content": 0.5, "ads": 0.3, "research": 0.2},
                "created_task_id": task.id,
            },
            messages=["Generated mock daily priorities and assignments."],
        )
