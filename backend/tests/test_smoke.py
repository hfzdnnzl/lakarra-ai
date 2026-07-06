"""Smoke tests for the Phase 1 scaffold."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.agents import registry as agent_registry
from app.main import app

client = TestClient(app)

EXPECTED_AGENTS = {
    "ceo",
    "marketing_manager",
    "content_analyst",
    "content_creator",
    "ad_manager",
    "product_research",
    "card_designer",
    "software_tester",
}


def test_health() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["memory_backend"] == "in_memory"


def test_all_agents_registered() -> None:
    assert EXPECTED_AGENTS.issubset(set(agent_registry.names()))


def test_list_agents_endpoint() -> None:
    resp = client.get("/api/agents")
    assert resp.status_code == 200
    names = {a["name"] for a in resp.json()}
    assert EXPECTED_AGENTS.issubset(names)


def test_invoke_ceo_agent() -> None:
    resp = client.post("/api/agents/ceo/invoke", json={"payload": {}})
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent"] == "ceo"
    assert "priorities" in body["output"]


def test_run_daily_priorities_workflow() -> None:
    resp = client.post("/api/workflows/daily_priorities/run", json={"payload": {}})
    assert resp.status_code == 200
    state = resp.json()
    assert state["status"] == "completed"
    # CEO, Marketing, Content Analyst, Product Research => 4 steps.
    assert len(state["steps"]) == 4
    assert "ceo" in state["results"]


def test_content_pipeline_requires_approval() -> None:
    resp = client.post(
        "/api/workflows/content_pipeline/run",
        json={"payload": {}, "thread_id": "test-approval"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "awaiting_approval"

    # An approval should now be queued.
    approvals = client.get("/api/approvals").json()
    assert any(a["workflow"] == "content_pipeline" for a in approvals)
