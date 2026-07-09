"""Content Analyst Agent — Phase 3.

Observes, analyzes, critiques, and learns from TikTok content. Produces structured
insights and recommendations only — NEVER generates scripts, captions, or storyboards.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import ValidationError

from ...config import effective_video_analysis_model, effective_video_analysis_provider, get_settings
from ...errors import LakarraError, OutputValidationError
from ...models.analytics import (
    CompetitorAnalysisPayload,
    PatternAnalysisPayload,
    ReviewReportPayload,
    TrendReportPayload,
)
from ...models.content_analysis import (
    MetricsPassOutput,
    VisualPassOutput,
)
from ...models.content import PerformanceReviewPayload
from ...models.db import Content
from ...models.domain import Report
from ...providers import (
    CompetitorProvider,
    InternalContentProvider,
    TikTokProvider,
    TikTokVideoData,
    build_competitor_provider,
)
from ...services.json_utils import extract_json
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


@dataclass
class AgentAnalysisResult:
    """Generic result from an analyst LLM call."""

    payload: dict
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


def _format_content_plan(content: Content) -> str:
    scenes = "\n".join(
        f"  Scene {s.sequence_number}: {s.start_time}-{s.end_time}s — {s.scene_description}"
        for s in content.scenes
    )
    return (
        f"Title: {content.title}\n"
        f"Category: {content.category}\n"
        f"Hook: {content.hook}\n"
        f"Duration: {content.duration}s\n"
        f"Caption: {content.caption}\n"
        f"Hashtags: {', '.join(content.hashtags)}\n"
        f"CTA: {content.cta}\n"
        f"Posting time: {content.posting_time}\n"
        f"Target audience: {content.target_audience}\n"
        f"Scenes:\n{scenes or '  (none)'}"
    )


@register_agent
class ContentAnalystAgent(BaseAgent):
    name = "content_analyst"
    role = "Content Analyst"
    description = (
        "Analyzes TikTok performance, competitors, and content plans. "
        "Produces insights only — never creates content."
    )
    prompt_name = "content_analyst"

    def __init__(
        self,
        context,
        *,
        tiktok: TikTokProvider | None = None,
        competitor: CompetitorProvider | None = None,
        internal: InternalContentProvider | None = None,
    ) -> None:
        super().__init__(context)
        self._tiktok = tiktok
        self._competitor = competitor or build_competitor_provider()
        self._internal = internal

    def set_internal_provider(self, provider: InternalContentProvider) -> None:
        self._internal = provider

    def set_tiktok_provider(self, provider: TikTokProvider) -> None:
        self._tiktok = provider

    def _tiktok_or_raise(self) -> TikTokProvider:
        if self._tiktok is None:
            from ...errors import MissingAccountHandleError

            raise MissingAccountHandleError(
                "No TikTok account connected. Set your @handle in Analytics settings."
            )
        return self._tiktok

    # --- LLM analysis helpers ---------------------------------------------
    def _run_prompt(
        self,
        prompt_name: str,
        variables: dict[str, str],
        model_cls: type,
    ) -> AgentAnalysisResult:
        template = load_prompt(prompt_name)
        messages = [
            {"role": "system", "content": template.system},
            {"role": "user", "content": template.render_user(variables)},
        ]
        from ...services.llm.base import Message

        completion = self.complete(
            [Message(role=m["role"], content=m["content"]) for m in messages],
            temperature=0.3,
        )
        data = extract_json(completion.text)
        try:
            validated = model_cls(**data)
        except ValidationError as exc:
            first = exc.errors()[0]
            location = ".".join(str(part) for part in first.get("loc", ()))
            detail = first.get("msg", "invalid value")
            raise OutputValidationError(
                f"Analysis output failed validation at {location}: {detail}"
            ) from exc

        return AgentAnalysisResult(
            payload=validated.model_dump(),
            model=completion.model,
            provider=completion.provider,
            prompt_version=template.version,
        )

    # --- Video analysis (uploaded asset — existing path) ------------------
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

        provider = effective_video_analysis_provider()
        return AnalysisResult(
            review=review,
            model=effective_video_analysis_model(),
            provider=provider,
            prompt_version=template.version,
        )

    # --- Phase 3 analysis methods -----------------------------------------
    def analyze_video(
        self,
        video_id: str,
        *,
        content_id: str | None = None,
        historical_context: str = "",
    ) -> AgentAnalysisResult:
        """Analyze a published Lakarra TikTok video."""

        video_data = self._tiktok_or_raise().get_video(video_id)
        if video_data is None:
            from ...errors import NotFoundError

            raise NotFoundError(f"Video '{video_id}' not found.")

        return self._analyze_video_data(video_data, historical_context=historical_context)

    def analyze_account(self) -> AgentAnalysisResult:
        """Analyze historical Lakarra account performance and detect patterns."""

        account = self._tiktok_or_raise().get_account()
        video_history = json.dumps(
            [
                {
                    "video_id": v.video.video_id,
                    "title": v.video.title,
                    "category": v.video.content_category,
                    "views": v.performance.views,
                    "engagement": v.performance.likes + v.performance.comments,
                    "publish_date": v.video.publish_date,
                    "publish_time": v.video.publish_time,
                    "duration": v.video.duration,
                }
                for v in account.videos
            ],
            indent=2,
        )
        cms_content = ""
        if self._internal:
            posted = self._internal.list_posted_content(limit=20)
            cms_content = _format_past_posts(posted)

        return self._run_prompt(
            "content_analyst_account",
            {
                "account_summary": json.dumps(
                    {"handle": account.handle, "followers": account.follower_count},
                    indent=2,
                ),
                "video_history": video_history,
                "cms_content": cms_content or "(no CMS content)",
            },
            PatternAnalysisPayload,
        )

    def analyze_competitor(self, handle: str) -> AgentAnalysisResult:
        """Analyze a competitor TikTok account."""

        account = self._competitor.get_account(handle)
        lakarra = self._tiktok_or_raise().get_account()
        return self._run_prompt(
            "content_analyst_competitor",
            {
                "competitor_data": json.dumps(account.model_dump(), indent=2),
                "lakarra_context": json.dumps(
                    {
                        "handle": lakarra.handle,
                        "followers": lakarra.follower_count,
                        "top_categories": list(
                            {v.video.content_category for v in lakarra.videos[:3]}
                        ),
                    },
                    indent=2,
                ),
            },
            CompetitorAnalysisPayload,
        )

    def review_content(self, content: Content) -> AgentAnalysisResult:
        """Review Content Creator output — never rewrites content."""

        historical = ""
        if self._internal:
            posted = self._internal.list_posted_content(limit=10)
            historical = _format_past_posts(posted)

        return self._run_prompt(
            "content_analyst_review",
            {
                "content_plan": _format_content_plan(content),
                "historical_context": historical or "(no historical data)",
            },
            ReviewReportPayload,
        )

    def generate_trend_report(self, *, period: str = "30d") -> AgentAnalysisResult:
        """Generate a trend report from historical analysis."""

        account = self._tiktok_or_raise().get_account()
        pattern_result = self.analyze_account()
        recent = json.dumps(
            [
                {
                    "video_id": v.video.video_id,
                    "title": v.video.title,
                    "views": v.performance.views,
                    "category": v.video.content_category,
                }
                for v in account.videos[:5]
            ],
            indent=2,
        )
        metrics = json.dumps(
            {
                "total_videos": len(account.videos),
                "total_views": sum(v.performance.views for v in account.videos),
                "avg_views": sum(v.performance.views for v in account.videos)
                // max(len(account.videos), 1),
                "followers": account.follower_count,
            },
            indent=2,
        )
        return self._run_prompt(
            "content_analyst_trend",
            {
                "period": period,
                "pattern_data": json.dumps(pattern_result.payload, indent=2),
                "recent_analyses": recent,
                "account_metrics": metrics,
            },
            TrendReportPayload,
        )

    def _analyze_video_data(
        self,
        video_data: TikTokVideoData,
        *,
        historical_context: str = "",
    ) -> AgentAnalysisResult:
        return self._run_prompt(
            "content_analyst_video",
            {
                "video_data": json.dumps(video_data.video.model_dump(), indent=2),
                "performance_data": json.dumps(video_data.performance.model_dump(), indent=2),
                "comments": json.dumps(video_data.comments, indent=2),
                "historical_context": historical_context or "(no historical context)",
            },
            MetricsPassOutput,
        )

    def analyze_video_visual(
        self,
        *,
        video_bytes: bytes,
        mime_type: str,
        video_data: TikTokVideoData,
        content: Content | None = None,
    ) -> VisualPassOutput:
        """Multimodal visual review of a published video."""

        template = load_prompt("content_analyst_video_visual")
        plan_context = "(no CMS plan linked)"
        if content is not None:
            plan_context = (
                f"Title: {content.title}\n"
                f"Category: {content.category}\n"
                f"Hook: {content.hook}\n"
                f"Duration: {content.duration}s\n"
                f"Caption: {content.caption}\n"
                f"CTA: {content.cta}"
            )
        performance_summary = json.dumps(
            {
                "views": video_data.performance.views,
                "completion_rate": video_data.performance.completion_rate,
                "average_watch_duration": video_data.performance.average_watch_duration,
                "likes": video_data.performance.likes,
                "comments": video_data.performance.comments,
                "shares": video_data.performance.shares,
                "saves": video_data.performance.saves,
            },
            indent=2,
        )
        user_prompt = template.render_user(
            {
                "duration": str(video_data.video.duration),
                "plan_context": plan_context,
                "performance_summary": performance_summary,
            }
        )
        review_prompt = f"{template.system}\n\n{user_prompt}"
        plan_json = json.dumps(
            {
                "video_id": video_data.video.video_id,
                "title": video_data.video.title,
                "caption": video_data.video.caption,
                "duration": video_data.video.duration,
                "content_category": video_data.video.content_category,
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
            return VisualPassOutput(**data)
        except ValidationError as exc:
            first = exc.errors()[0]
            location = ".".join(str(part) for part in first.get("loc", ()))
            detail = first.get("msg", "invalid value")
            raise OutputValidationError(
                f"Visual analysis output failed validation at {location}: {detail}"
            ) from exc

    def analyze_all_videos(self) -> list[AgentAnalysisResult]:
        """Analyze every published video on the Lakarra account."""

        return [
            self._analyze_video_data(v)
            for v in self._tiktok_or_raise().get_account().videos
        ]

    # --- Workflow entry point -----------------------------------------------
    def handle(self, request: AgentRequest) -> AgentResult:
        action = request.payload.get("action", "account")

        try:
            if action == "video":
                video_id = request.payload.get("video_id", "lk-001")
                result = self.analyze_video(video_id)
                output = {"action": "video", "video_id": video_id, "analysis": result.payload}
            elif action == "competitor":
                handle = request.payload.get("handle", "paperlesspost")
                result = self.analyze_competitor(handle)
                output = {"action": "competitor", "handle": handle, "analysis": result.payload}
            elif action == "trend":
                period = request.payload.get("period", "30d")
                result = self.generate_trend_report(period=period)
                output = {"action": "trend", "period": period, "report": result.payload}
            else:
                result = self.analyze_account()
                output = {"action": "account", "patterns": result.payload}

            self.context.memory.reports.add(
                Report(
                    agent=self.name,
                    title=f"Content analysis: {action}",
                    summary=output.get("analysis", output.get("patterns", output.get("report", {})))
                    .get("summary", "Analysis complete."),
                    payload=output,
                )
            )

            return AgentResult(
                agent=self.name,
                output=output,
                messages=[f"Completed {action} analysis."],
            )
        except LakarraError as exc:
            return AgentResult(
                agent=self.name,
                output={"error": exc.message, "error_type": exc.error_type},
                messages=[exc.message],
            )
