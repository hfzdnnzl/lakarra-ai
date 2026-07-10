"""Content Analyst Agent — Phase 3.

Observes, analyzes, critiques, and learns from TikTok content. Produces structured
insights and recommendations only — NEVER generates scripts, captions, or storyboards.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import ValidationError

from ...config import effective_visual_analysis_model, effective_visual_analysis_provider, get_settings
from ...errors import LakarraError, OutputValidationError
from ...models.analytics import (
    CompetitorAnalysisPayload,
    PatternAnalysisPayload,
    ReviewReportPayload,
    TrendReportPayload,
)
from ...models.content_analysis import (
    ContentAnalysisInput,
    ContentType,
    MediaSource,
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
from ...services.content_visual_analysis import (
    VisualAnalysisContext,
    build_content_visual_analysis_service,
    parse_review_json,
    resolve_visual_prompt_key,
)
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
        analyzer = build_content_visual_analysis_service()
        raw = analyzer.analyze_visual(
            content_type=ContentType.VIDEO,
            media=MediaSource(bytes=video_bytes, mime_type=mime_type),
            context=VisualAnalysisContext(
                review_prompt=review_prompt,
                plan_json=plan_json,
                mode="performance",
            ),
        )
        data = parse_review_json(raw)
        try:
            review = PerformanceReviewPayload(**data)
        except ValidationError as exc:
            raise OutputValidationError(
                f"Performance review failed validation: {exc.error_count()} error(s)."
            ) from exc

        provider = effective_visual_analysis_provider()
        return AnalysisResult(
            review=review,
            model=effective_visual_analysis_model(),
            provider=provider,
            prompt_version=template.version,
        )

    # --- Unified content analysis (VIDEO + IMAGE) -------------------------
    def _run_metrics_pass(self, input_data: ContentAnalysisInput) -> AgentAnalysisResult:
        return self._run_prompt(
            "content_analyst/metrics",
            {
                "content_type": input_data.content_type.value,
                "post_data": json.dumps(input_data.content_metadata.model_dump(), indent=2),
                "performance_data": json.dumps(
                    input_data.performance_data.model_dump(), indent=2
                ),
                "comments": json.dumps(input_data.comments, indent=2),
                "historical_context": input_data.historical_context or "(no historical context)",
            },
            MetricsPassOutput,
        )

    def analyze_visual_content(
        self,
        input_data: ContentAnalysisInput,
        media: MediaSource,
    ) -> VisualPassOutput:
        """Multimodal visual review of published VIDEO or IMAGE content."""

        prompt_name = resolve_visual_prompt_key(input_data.content_type)
        template = load_prompt(prompt_name)
        plan_context = "(no CMS plan linked)"
        if input_data.linked_content_id and self._internal:
            content = self._internal.get_content(input_data.linked_content_id)
            if content is not None:
                plan_context = (
                    f"Title: {content.title}\n"
                    f"Category: {content.category}\n"
                    f"Hook: {content.hook}\n"
                    f"Caption: {content.caption}\n"
                    f"CTA: {content.cta}"
                )
        performance_summary = json.dumps(
            {
                "views": input_data.performance_data.views,
                "completion_rate": input_data.performance_data.completion_rate,
                "average_watch_duration": input_data.performance_data.average_watch_duration,
                "likes": input_data.performance_data.likes,
                "comments": input_data.performance_data.comments,
                "shares": input_data.performance_data.shares,
                "saves": input_data.performance_data.saves,
            },
            indent=2,
        )
        variables: dict[str, str] = {
            "plan_context": plan_context,
            "performance_summary": performance_summary,
        }
        if input_data.content_type == ContentType.VIDEO:
            variables["duration"] = str(input_data.content_metadata.duration)

        user_prompt = template.render_user(variables)
        review_prompt = f"{template.system}\n\n{user_prompt}"
        plan_json = json.dumps(input_data.content_metadata.model_dump(), indent=2)

        analyzer = build_content_visual_analysis_service()
        raw = analyzer.analyze_visual(
            content_type=input_data.content_type,
            media=media,
            context=VisualAnalysisContext(
                review_prompt=review_prompt,
                plan_json=plan_json,
            ),
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

    def analyze_content(self, input_data: ContentAnalysisInput) -> AgentAnalysisResult:
        """Run Pass 1 metrics analysis for VIDEO or IMAGE content."""

        return self._run_metrics_pass(input_data)

    # --- Phase 3 analysis methods -----------------------------------------
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

    def analyze_all_posts(self) -> list[AgentAnalysisResult]:
        """Analyze every published post on the Lakarra account."""

        results: list[AgentAnalysisResult] = []
        for post_data in self._tiktok_or_raise().get_account().videos:
            from .input_builder import build_content_analysis_input

            input_data = ContentAnalysisInput(
                content_type=getattr(
                    post_data.video, "content_type", ContentType.VIDEO
                ),
                post_id=post_data.video.post_id,
                content_metadata=post_data.video,
                performance_data=post_data.performance,
                comments=list(post_data.comments),
                historical_context="",
            )
            results.append(self._run_metrics_pass(input_data))
        return results

    # --- Workflow entry point -----------------------------------------------
    def handle(self, request: AgentRequest) -> AgentResult:
        action = request.payload.get("action", "account")

        try:
            from ...errors import NotFoundError

            if action == "video":
                video_id = request.payload.get("video_id", "lk-001")
                post_data = self._tiktok_or_raise().get_video(video_id)
                if post_data is None:
                    raise NotFoundError(f"Post '{video_id}' not found.")
                input_data = ContentAnalysisInput(
                    content_type=getattr(post_data.video, "content_type", ContentType.VIDEO),
                    post_id=post_data.video.post_id,
                    content_metadata=post_data.video,
                    performance_data=post_data.performance,
                    comments=list(post_data.comments),
                )
                result = self.analyze_content(input_data)
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
