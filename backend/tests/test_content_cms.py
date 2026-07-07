"""Tests for the Content Management System (Phase 2.5)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.agents.base import AgentContext
from app.agents.content_creator import ContentCreatorAgent
from app.main import app
from app.memory import get_memory
from app.models.content import ContentRequest
from app.services.content_service import ContentService
from app.services.llm.base import CompletionResult, LLMProvider, Message
from app.tools import registry as tool_registry

client = TestClient(app)


def _plan(hook: str, title: str = "Test plan") -> dict:
    return {
        "title": title,
        "category": "pov",
        "target_audience": "Malaysian couples aged 23-35",
        "hook": hook,
        "duration": 10,
        "timeline": [
            {"start": 0, "end": 5, "scene": "Before", "camera": "cu", "text": "a"},
            {"start": 5, "end": 10, "scene": "After", "camera": "zoom", "text": "b"},
        ],
        "caption": "caption",
        "hashtags": ["#lakarra"],
        "cta": "Link in bio",
        "posting_time": "Friday 8PM",
        "confidence": 0.9,
    }


class ScriptedLLM(LLMProvider):
    """Returns each provided response text on successive calls."""

    def __init__(self, texts: list[str]) -> None:
        super().__init__("scripted-model")
        self._texts = texts
        self._i = 0

    def complete(self, messages: list[Message], *, temperature: float = 0.7) -> CompletionResult:
        text = self._texts[min(self._i, len(self._texts) - 1)]
        self._i += 1
        return CompletionResult(text=text, model=self.model, provider="scripted")


def scripted_service(db_session, texts: list[str]) -> ContentService:
    agent = ContentCreatorAgent(
        AgentContext(memory=get_memory(), llm=ScriptedLLM(texts), tools=tool_registry)
    )
    return ContentService(db_session, agent=agent)


# --- persistence -----------------------------------------------------------
def test_generate_persists_content_scenes_and_metadata(db_session) -> None:
    service = scripted_service(db_session, [json.dumps(_plan("Hook A"))])
    resp = service.generate(ContentRequest(business_goal="Increase engagement"))
    assert resp.success and resp.content_id

    content = service.get(resp.content_id)
    assert content is not None
    assert content.status == "draft"
    assert content.active_version == 1
    assert len(content.scenes) == 2
    assert content.scenes[0].sequence_number == 1
    assert len(service.versions(resp.content_id)) == 1
    assert len(service.generations(resp.content_id)) == 1
    # Creation is recorded in status history (None -> draft).
    history = service.status_history(resp.content_id)
    assert history[0].old_status is None and history[0].new_status == "draft"


# --- versioning ------------------------------------------------------------
def test_regeneration_creates_new_active_version(db_session) -> None:
    texts = [json.dumps(_plan("Hook A")), json.dumps(_plan("Hook B"))]
    service = scripted_service(db_session, texts)
    first = service.generate(ContentRequest(business_goal="goal"))
    second = service.generate(ContentRequest(business_goal="goal"), content_id=first.content_id)
    assert second.content_id == first.content_id

    content = service.get(first.content_id)
    assert content.active_version == 2
    assert content.hook == "Hook B"
    versions = service.versions(first.content_id)
    assert [v.version_number for v in versions] == [1, 2]
    assert sum(1 for v in versions if v.is_active) == 1


def test_activate_version_restores_snapshot(db_session) -> None:
    texts = [json.dumps(_plan("Hook A")), json.dumps(_plan("Hook B"))]
    service = scripted_service(db_session, texts)
    first = service.generate(ContentRequest(business_goal="goal"))
    service.generate(ContentRequest(business_goal="goal"), content_id=first.content_id)

    content = service.activate_version(first.content_id, 1)
    assert content.active_version == 1
    assert content.hook == "Hook A"
    versions = {v.version_number: v.is_active for v in service.versions(first.content_id)}
    assert versions[1] is True and versions[2] is False


# --- status ----------------------------------------------------------------
def test_update_status_records_history(db_session) -> None:
    service = scripted_service(db_session, [json.dumps(_plan("Hook A"))])
    created = service.generate(ContentRequest(business_goal="goal"))
    service.update_status(created.content_id, new_status="review", changed_by="alice", comment="ok")
    content = service.get(created.content_id)
    assert content.status == "review"
    history = service.status_history(created.content_id)
    assert history[-1].old_status == "draft"
    assert history[-1].new_status == "review"
    assert history[-1].changed_by == "alice"


# --- feedback --------------------------------------------------------------
def test_feedback_storage(db_session) -> None:
    service = scripted_service(db_session, [json.dumps(_plan("Hook A"))])
    created = service.generate(ContentRequest(business_goal="goal"))
    service.add_feedback(created.content_id, message="Hook is too weak", created_by="bob")
    feedback = service.feedback(created.content_id)
    assert len(feedback) == 1
    assert feedback[0].message == "Hook is too weak"
    assert feedback[0].created_by == "bob"


# --- pagination / filtering ------------------------------------------------
def test_pagination_and_total(db_session) -> None:
    service = scripted_service(db_session, [json.dumps(_plan("Hook A"))] * 3)
    for _ in range(3):
        service.generate(ContentRequest(business_goal="goal"))
    items, total = service.list(
        page=1, page_size=2, search=None, category=None, status=None, sort="-created_at"
    )
    assert total == 3
    assert len(items) == 2
    items2, _ = service.list(
        page=2, page_size=2, search=None, category=None, status=None, sort="-created_at"
    )
    assert len(items2) == 1


def test_filter_by_status(db_session) -> None:
    service = scripted_service(db_session, [json.dumps(_plan("Hook A"))] * 2)
    a = service.generate(ContentRequest(business_goal="goal"))
    service.generate(ContentRequest(business_goal="goal"))
    service.update_status(a.content_id, new_status="posted", changed_by="user", comment=None)
    items, total = service.list(
        page=1, page_size=10, search=None, category=None, status="posted", sort="-created_at"
    )
    assert total == 1
    assert items[0].id == a.content_id


# --- API -------------------------------------------------------------------
def test_api_generate_returns_content_id() -> None:
    resp = client.post("/api/content/generate", json={"business_goal": "Increase engagement"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["content_id"]


def test_api_library_and_detail_and_status_and_feedback() -> None:
    gen = client.post("/api/content/generate", json={"business_goal": "Increase engagement"})
    content_id = gen.json()["content_id"]

    # Library (paginated)
    lib = client.get("/api/content", params={"page": 1, "page_size": 5})
    assert lib.status_code == 200
    lib_body = lib.json()
    assert lib_body["total"] >= 1
    assert len(lib_body["items"]) <= 5

    # Detail
    detail = client.get(f"/api/content/{content_id}")
    assert detail.status_code == 200
    assert detail.json()["scenes"]

    # Status update
    patched = client.patch(f"/api/content/{content_id}/status", json={"status": "review"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "review"

    # Versions
    versions = client.get(f"/api/content/{content_id}/versions")
    assert versions.status_code == 200
    assert len(versions.json()) == 1

    # Feedback
    fb = client.post(f"/api/content/{content_id}/feedback", json={"message": "Need more emotion"})
    assert fb.status_code == 201
    fb_list = client.get(f"/api/content/{content_id}/feedback")
    assert len(fb_list.json()) == 1


def test_api_detail_404() -> None:
    resp = client.get("/api/content/does-not-exist")
    assert resp.status_code == 404
