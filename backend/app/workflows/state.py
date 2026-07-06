"""Workflow state definitions used by the LangGraph engine."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class WorkflowState(TypedDict, total=False):
    """State object threaded through a workflow graph.

    ``steps`` accumulates one entry per executed node (using an additive reducer),
    while ``results`` maps an agent name to its latest structured output.
    """

    workflow: str
    payload: dict[str, Any]
    steps: Annotated[list[dict[str, Any]], operator.add]
    results: dict[str, Any]
    status: str
