"""Content Creator Agent.

The first production-ready agent. It turns a business brief into a complete,
validated TikTok content plan by:

1. loading its file-based prompts,
2. calling the configured LLM provider,
3. parsing and validating the JSON output into a :class:`ContentIdea`.

This establishes the pattern future agents will follow (extend :class:`BaseAgent`,
load prompts, call the LLM, validate output, return a structured model).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from pydantic import ValidationError

from ...config import effective_visual_analysis_model, effective_visual_analysis_provider, get_settings
from ...errors import EmptyResponseError, OutputValidationError
from ...models.content import ContentIdea, ContentRequest, FidelityReviewPayload
from ...models.db import Content
from ...services.json_utils import extract_json
from ...services.llm.base import Message
from ...services.prompts import load_prompt
from ...services.video_analysis import build_video_analysis_service, parse_review_json
from ..base import AgentRequest, AgentResult, BaseAgent
from ..registry import register_agent


@dataclass
class GenerationResult:
    """The validated idea plus metadata for logging."""

    idea: ContentIdea
    model: str
    provider: str
    prompt_version: str
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class ReviewResult:
    review: FidelityReviewPayload
    model: str
    provider: str
    prompt_version: str


@register_agent
class ContentCreatorAgent(BaseAgent):
    name = "content_creator"
    role = "Content Creator"
    description = "Generates structured TikTok content plans from a business brief."
    prompt_name = "content_creator"

    def generate(self, request: ContentRequest, *, temperature: float = 0.7) -> GenerationResult:
        """Generate and validate a content plan for ``request``."""

        template = self.load_prompt()
        constraints = (
            "\n".join(f"- {c}" for c in request.constraints)
            if request.constraints
            else "- (no additional constraints)"
        )
        audience = request.target_audience or "Malaysian couples aged 23-35"
        messages = [
            Message(role="system", content=template.system),
            Message(
                role="user",
                content=template.render_user(
                    {
                        "business_goal": request.business_goal,
                        "target_audience": audience,
                        "product": request.product,
                        "constraints": constraints,
                    }
                ),
            ),
        ]

        completion = self.complete(messages, temperature=temperature)

        if not completion.text or not completion.text.strip():
            raise EmptyResponseError("The LLM returned an empty response.")

        data = extract_json(completion.text)  # raises InvalidJSONError on failure

        try:
            idea = ContentIdea(**data)
        except ValidationError as exc:
            raise OutputValidationError(
                f"Generated content failed validation: {exc.error_count()} error(s)."
            ) from exc

        return GenerationResult(
            idea=idea,
            model=completion.model,
            provider=completion.provider,
            prompt_version=template.version,
            usage=completion.usage,
        )

    def review_asset(
        self,
        content: Content,
        *,
        video_bytes: bytes,
        mime_type: str,
    ) -> ReviewResult:
        """Compare an uploaded video against the persisted content plan."""

        template = load_prompt("content_creator_review")
        plan = {
            "title": content.title,
            "category": content.category,
            "hook": content.hook,
            "duration": content.duration,
            "timeline": [
                {
                    "start": s.start_time,
                    "end": s.end_time,
                    "scene": s.scene_description,
                    "camera": s.camera_direction,
                    "text": s.on_screen_text,
                    "voiceover": s.voiceover,
                    "sound_effect": s.sound_effect,
                }
                for s in sorted(content.scenes, key=lambda x: x.sequence_number)
            ],
            "caption": content.caption,
            "cta": content.cta,
        }
        user_prompt = template.render_user(
            {
                "title": content.title,
                "category": content.category,
                "hook": content.hook,
                "duration": str(content.duration),
            }
        )
        review_prompt = f"{template.system}\n\n{user_prompt}"
        analyzer = build_video_analysis_service()
        raw = analyzer.analyze(
            video_bytes=video_bytes,
            mime_type=mime_type,
            plan_json=json.dumps(plan, indent=2),
            review_prompt=review_prompt,
        )
        data = parse_review_json(raw)
        try:
            review = FidelityReviewPayload(**data)
        except ValidationError as exc:
            raise OutputValidationError(
                f"Fidelity review failed validation: {exc.error_count()} error(s)."
            ) from exc

        settings = get_settings()
        return ReviewResult(
            review=review,
            model=effective_visual_analysis_model(),
            provider=effective_visual_analysis_provider(),
            prompt_version=template.version,
        )

    def handle(self, request: AgentRequest) -> AgentResult:
        """Workflow-compatible entry point (used by the LangGraph engine)."""

        payload = request.payload or {}
        content_request = ContentRequest(
            business_goal=payload.get("business_goal", "Increase engagement"),
            target_audience=payload.get("target_audience", ""),
            product=payload.get("product", "Digital Wedding Invitation"),
            constraints=payload.get("constraints", []),
        )
        result = self.generate(content_request)
        return AgentResult(
            agent=self.name,
            output=result.idea.model_dump(mode="json"),
            messages=[f"Generated content plan with {result.model} ({result.prompt_version})."],
        )
