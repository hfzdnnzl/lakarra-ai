"""Tests for the Content Creator agent, service and API (Phase 2)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.agents.base import AgentContext
from app.agents.content_creator import ContentCreatorAgent
from app.errors import EmptyResponseError, InvalidJSONError, OutputValidationError
from app.main import app
from app.memory import get_memory
from app.models.content import ContentIdea, ContentRequest, TimelineScene
from app.services.content_creator_service import ContentCreatorService
from app.services.json_utils import extract_json
from app.services.llm.base import CompletionResult, LLMProvider, Message
from app.services.prompts import load_prompt
from app.tools import registry as tool_registry

client = TestClient(app)

VALID_PLAN = {
    "title": "POV: Upgrade your wedding invite",
    "category": "pov",
    "target_audience": "Malaysian couples aged 23-35",
    "hook": "POV: your guests gasp at your invite",
    "duration": 10,
    "timeline": [
        {"start": 0, "end": 5, "scene": "Boring PDF", "camera": "close-up", "text": "Before"},
        {"start": 5, "end": 10, "scene": "Animated invite", "camera": "zoom", "text": "After"},
    ],
    "caption": "Every love story deserves more than a PDF.",
    "hashtags": ["#wedding", "#lakarra"],
    "cta": "Link in bio",
    "posting_time": "Friday 8PM",
    "confidence": 0.9,
}


class StubLLM(LLMProvider):
    """LLM provider that returns a fixed response (for deterministic tests)."""

    def __init__(self, text: str) -> None:
        super().__init__("stub-model")
        self._text = text

    def complete(self, messages: list[Message], *, temperature: float = 0.7) -> CompletionResult:
        return CompletionResult(text=self._text, model=self.model, provider="stub")


def make_agent(text: str) -> ContentCreatorAgent:
    context = AgentContext(memory=get_memory(), llm=StubLLM(text), tools=tool_registry)
    return ContentCreatorAgent(context)


# --- prompt loading --------------------------------------------------------
def test_prompt_loading() -> None:
    template = load_prompt("content_creator")
    assert template.system.strip()
    assert "{{business_goal}}" in template.user
    assert template.version.startswith("content_creator@")


def test_prompt_rendering_replaces_tokens() -> None:
    template = load_prompt("content_creator")
    rendered = template.render_user({"business_goal": "Grow reach", "constraints": "- fast"})
    assert "Grow reach" in rendered
    assert "{{business_goal}}" not in rendered


# --- JSON parsing ----------------------------------------------------------
def test_extract_json_plain() -> None:
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_code_fence() -> None:
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_prose() -> None:
    assert extract_json('Here you go:\n{"a": 1}\nThanks!') == {"a": 1}


def test_extract_json_invalid_raises() -> None:
    with pytest.raises(InvalidJSONError):
        extract_json("not json at all")


# --- output validation -----------------------------------------------------
def test_content_idea_accepts_valid() -> None:
    idea = ContentIdea(**VALID_PLAN)
    assert idea.duration == 10
    assert len(idea.timeline) == 2


def test_timeline_scene_rejects_bad_bounds() -> None:
    with pytest.raises(ValidationError):
        TimelineScene(start=5, end=3, scene="x")


def test_content_idea_rejects_bad_category() -> None:
    bad = {**VALID_PLAN, "category": "not_a_category"}
    with pytest.raises(ValidationError):
        ContentIdea(**bad)


def test_content_idea_rejects_confidence_out_of_range() -> None:
    bad = {**VALID_PLAN, "confidence": 1.5}
    with pytest.raises(ValidationError):
        ContentIdea(**bad)


def test_content_idea_rejects_timeline_beyond_duration() -> None:
    bad = {**VALID_PLAN, "duration": 8}  # timeline ends at 10 > 8
    with pytest.raises(ValidationError):
        ContentIdea(**bad)


# --- timeline generation (agent) ------------------------------------------
def test_agent_generate_with_mock_provider() -> None:
    from app.agents import get_agent_context

    agent = ContentCreatorAgent(get_agent_context())  # uses the default mock provider
    request = ContentRequest(
        business_goal="Increase engagement",
        target_audience="Malaysian couples aged 23-35",
        product="Digital Wedding Invitation",
        constraints=["Simple aesthetic", "Less than 15 seconds"],
    )
    result = agent.generate(request)
    idea = result.idea
    assert len(idea.timeline) >= 1
    # Timeline must cover the full declared duration and be well-formed.
    assert idea.timeline[-1].end == idea.duration
    for scene in idea.timeline:
        assert scene.end > scene.start
    # Mock is request-aware: it echoes the target audience.
    assert idea.target_audience == "Malaysian couples aged 23-35"
    assert result.usage  # token usage is populated


def test_agent_raises_on_invalid_json() -> None:
    with pytest.raises(InvalidJSONError):
        make_agent("totally not json").generate(ContentRequest(business_goal="x"))


def test_agent_raises_on_empty_response() -> None:
    with pytest.raises(EmptyResponseError):
        make_agent("   ").generate(ContentRequest(business_goal="x"))


def test_agent_raises_on_schema_violation() -> None:
    import json

    bad_plan = {"title": "missing most fields"}
    with pytest.raises(OutputValidationError):
        make_agent(json.dumps(bad_plan)).generate(ContentRequest(business_goal="x"))


# --- service ---------------------------------------------------------------
def test_service_success() -> None:
    import json

    service = ContentCreatorService(make_agent(json.dumps(VALID_PLAN)))
    response = service.generate(ContentRequest(business_goal="Increase engagement"))
    assert response.success is True
    assert response.data is not None
    assert response.data.title == VALID_PLAN["title"]


def test_service_failure_returns_error_type() -> None:
    service = ContentCreatorService(make_agent("nope"))
    response = service.generate(ContentRequest(business_goal="Increase engagement"))
    assert response.success is False
    assert response.error_type == "invalid_json"


# --- API -------------------------------------------------------------------
def test_api_generate_success() -> None:
    resp = client.post(
        "/api/content/generate",
        json={
            "business_goal": "Increase engagement",
            "target_audience": "Malaysian couples aged 23-35",
            "product": "Digital Wedding Invitation",
            "constraints": ["Simple aesthetic", "Less than 15 seconds"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["title"]
    assert data["category"] in {
        "aesthetic",
        "educational",
        "product_comparison",
        "pov",
        "testimonial",
        "storytelling",
        "behind_the_scenes",
        "trend_adaptation",
    }
    assert len(data["timeline"]) >= 1
    assert 0.0 <= data["confidence"] <= 1.0


def test_api_generate_rejects_empty_goal() -> None:
    resp = client.post("/api/content/generate", json={"business_goal": ""})
    assert resp.status_code == 422  # request-body validation
