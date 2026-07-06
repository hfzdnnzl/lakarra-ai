"""Configurable workflow definitions.

Workflows are *data*, not hardcoded graphs: a :class:`WorkflowDefinition` lists the
ordered agent steps and options (approval gate, retries). The engine compiles the
definition into a LangGraph graph. New workflows are added by registering another
definition -- no engine changes required.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkflowStep:
    """A single node in a workflow: run one agent."""

    agent: str
    #: Number of automatic retries if the agent raises.
    retries: int = 1


@dataclass
class WorkflowDefinition:
    """An ordered, configurable sequence of agent steps."""

    name: str
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    #: When true the graph pauses for human approval before finishing.
    requires_approval: bool = False


#: Example: the "morning priorities" workflow described in the architecture.
DAILY_PRIORITIES = WorkflowDefinition(
    name="daily_priorities",
    description="Every morning: CEO -> Marketing -> Content Analyst -> Product Research.",
    steps=[
        WorkflowStep(agent="ceo"),
        WorkflowStep(agent="marketing_manager"),
        WorkflowStep(agent="content_analyst"),
        WorkflowStep(agent="product_research"),
    ],
)

#: Example: content creation pipeline that requires human approval before posting.
CONTENT_PIPELINE = WorkflowDefinition(
    name="content_pipeline",
    description="Create content, critique it, then require approval before posting.",
    steps=[
        WorkflowStep(agent="marketing_manager"),
        WorkflowStep(agent="content_creator"),
        WorkflowStep(agent="content_analyst"),
    ],
    requires_approval=True,
)
