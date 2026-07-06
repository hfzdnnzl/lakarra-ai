"""Agent routes: list agents and invoke a single agent directly."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...agents import AgentRequest, get_agent_context, registry

router = APIRouter(prefix="/agents", tags=["agents"])


class InvokePayload(BaseModel):
    payload: dict = {}


@router.get("")
def list_agents() -> list[dict]:
    context = get_agent_context()
    return [agent.describe() for agent in registry.instantiate_all(context).values()]


@router.post("/{name}/invoke")
def invoke_agent(name: str, body: InvokePayload) -> dict:
    context = get_agent_context()
    agent = registry.instantiate(name, context)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {name}")
    result = agent.handle(AgentRequest(payload=body.payload))
    return result.model_dump(mode="json")
