"""Content Analyst Agent.

Analyzes TikTok content performance and critiques uploaded videos. Produces
structured feedback only — it never generates content or rejects content.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import ValidationError

from ...config import get_settings
from ...errors import OutputValidationError
from ...models.content import PerformanceReviewPayload
from ...models.db import Content
from ...models.domain import Report
from ...services.prompts import load_prompt
from ...services.video_analysis import build_video_analysis_service, parse_review_json
from ..base import AgentRequest, AgentResult, BaseAgent
from ..registry import register_agent


@dataclass
class AnalysisResult:
    review: PerformanceReviewPayload
    model: str
    provider: str
    prompt_version: str


def _format_past_posts(posts: list[Content]) -> str:
    if not posts:
        return "- (no posted content yet — compare against plan patterns only)"
    lines = []
    for post in posts:
        note = f" — notes: {post.performance_notes}" if post.performance_notes else ""
        lines.append(
            f"- [{post.status}] {post.title} ({post.category}, {post.duration}s, "
            f"hook: {post.hook[:80]}){note}"
        )
    return "\n".join(lines)


@register_agent
class ContentAnalystAgent(BaseAgent):
    name = "content_analyst"
    role = "Content Analyst"
    description = "Analyzes TikTok performance and critiques content. Never creates content."
    prompt_name = "content_analyst"

    def analyze_asset(
        self,
        content: Content,
        *,
        video_bytes: bytes,
        mime_type: str,
        past_posts: list[Content],
    ) -> AnalysisResult:
        """Predict performance of an uploaded video using plan + past post context."""

        template = load_prompt(self.prompt_name)
        plan_summary = (
            f"Title: {content.title}\n"
            f"Category: {content.category}\n"
            f"Hook: {content.hook}\n"
            f"Duration: {content.duration}s\n"
            f"Caption: {content.caption}\n"
            f"CTA: {content.cta}\n"
            f"Posting time: {content.posting_time}"
        )
        user_prompt = template.render_user(
            {
                "plan_summary": plan_summary,
                "past_posts": _format_past_posts(past_posts),
            }
        )
        review_prompt = f"{template.system}\n\n{user_prompt}"
        plan_json = json.dumps(
            {
                "title": content.title,
                "category": content.category,
                "hook": content.hook,
                "duration": content.duration,
                "caption": content.caption,
                "hashtags": content.hashtags,
                "posting_time": content.posting_time,
            },
            indent=2,
        )
        analyzer = build_video_analysis_service()
        raw = analyzer.analyze(
            video_bytes=video_bytes,
            mime_type=mime_type,
            plan_json=plan_json,
            review_prompt=review_prompt,
        )
        data = parse_review_json(raw)
        try:
            review = PerformanceReviewPayload(**data)
        except ValidationError as exc:
            raise OutputValidationError(
                f"Performance review failed validation: {exc.error_count()} error(s)."
            ) from exc

        provider = get_settings().video_analysis_provider
        return AnalysisResult(
            review=review,
            model=get_settings().video_analysis_model,
            provider=provider,
            prompt_version=template.version,
        )

    def handle(self, request: AgentRequest) -> AgentResult:
        feedback = {
            "hook_strength": 0.7,
            "emotional_triggers": ["nostalgia", "excitement"],
            "why_it_worked": ["Strong 1s hook", "Clear payoff"],
            "why_it_failed": [],
            "common_patterns": ["Fast cuts", "Text-on-screen captions"],
            "best_posting_times": ["18:00", "20:00"],
        }

        self.context.memory.reports.add(
            Report(
                agent=self.name,
                title="Content analysis",
                summary="Mock structured content feedback.",
                payload=feedback,
            )
        )

        return AgentResult(
            agent=self.name,
            output={"feedback": feedback},
            messages=["Produced mock structured feedback."],
        )
