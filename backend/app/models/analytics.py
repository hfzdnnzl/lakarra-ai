"""Pydantic models for the Content Analyst agent (Phase 3).

Defines structured analysis contracts for TikTok videos, competitors, trends,
content reviews, and historical analytics. The agent produces these payloads —
it never generates content.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field, field_validator


def normalize_tiktok_handle(value: str) -> str:
    """Strip @ and whitespace; lowercase for consistent lookups."""

    return value.strip().lstrip("@").lower()


def coerce_str_list(value: Any) -> list[str]:
    """Normalize LLM output where a list field is returned as a single string."""

    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                items.append(text)
        return items
    text = str(value).strip()
    return [text] if text else []


def normalize_unit_ratio(value: Any) -> float:
    """Accept 0–1 ratios or whole-number percentages from LLM JSON."""

    if value is None:
        return 0.0
    ratio = float(value)
    if ratio > 1.0 and ratio <= 100.0:
        return ratio / 100.0
    return ratio


from .content_types import ContentType


class ScoreWithExplanation(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    explanation: str

    @field_validator("score", mode="before")
    @classmethod
    def _normalize_score(cls, value: Any) -> float:
        return normalize_unit_ratio(value)


class PostInfo(BaseModel):
    """Published TikTok post metadata (video or image)."""

    post_id: str = Field(
        validation_alias=AliasChoices("post_id", "video_id"),
        serialization_alias="video_id",
    )
    content_type: ContentType = ContentType.VIDEO
    url: str = ""
    title: str = ""
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)

    @field_validator("hashtags", mode="before")
    @classmethod
    def _coerce_hashtags(cls, value: Any) -> list[str]:
        return coerce_str_list(value)

    publish_date: str = ""
    publish_time: str = ""
    duration: int = 0
    thumbnail: str = ""
    content_category: str = ""

    @property
    def video_id(self) -> str:
        """DB/API legacy name for post_id."""

        return self.post_id


VideoInfo = PostInfo


class PerformanceMetrics(BaseModel):
    views: int = 0
    reach: int = 0
    watch_time: float = 0.0
    average_watch_duration: float = 0.0
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    retention_curve: list[float] = Field(default_factory=list)

    @field_validator("completion_rate", mode="before")
    @classmethod
    def _normalize_completion_rate(cls, value: Any) -> float:
        return normalize_unit_ratio(value)
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    profile_visits: int = 0
    followers_gained: int = 0
    link_clicks: int | None = None


class EngagementMetrics(BaseModel):
    engagement_rate: float = 0.0
    share_rate: float = 0.0
    save_rate: float = 0.0
    like_to_view_ratio: float = 0.0
    comment_to_view_ratio: float = 0.0
    follower_conversion_rate: float = 0.0


class QualityScores(BaseModel):
    hook_score: ScoreWithExplanation
    retention_score: ScoreWithExplanation
    cta_score: ScoreWithExplanation
    pacing_score: ScoreWithExplanation
    storytelling_score: ScoreWithExplanation
    emotional_impact: ScoreWithExplanation
    educational_value: ScoreWithExplanation
    overall_content_health: ScoreWithExplanation


class RetentionAnalysis(BaseModel):
    strongest_timestamp: str = ""
    weakest_timestamp: str = ""
    drop_off_points: list[str] = Field(default_factory=list)
    pacing_issues: list[str] = Field(default_factory=list)
    scene_transition_issues: list[str] = Field(default_factory=list)

    @field_validator(
        "drop_off_points",
        "pacing_issues",
        "scene_transition_issues",
        mode="before",
    )
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return coerce_str_list(value)


class CommentIntelligence(BaseModel):
    sentiment: str = ""
    repeated_questions: list[str] = Field(default_factory=list)
    feature_requests: list[str] = Field(default_factory=list)
    customer_objections: list[str] = Field(default_factory=list)
    purchase_intent: str = ""
    most_common_keywords: list[str] = Field(default_factory=list)

    @field_validator(
        "repeated_questions",
        "feature_requests",
        "customer_objections",
        "most_common_keywords",
        mode="before",
    )
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return coerce_str_list(value)


class ContentRecommendations(BaseModel):
    content_categories: list[str] = Field(default_factory=list)
    content_angles: list[str] = Field(default_factory=list)
    hook_improvements: list[str] = Field(default_factory=list)
    posting_schedule: list[str] = Field(default_factory=list)
    experiments: list[str] = Field(default_factory=list)
    strategy_gaps: list[str] = Field(default_factory=list)

    @field_validator(
        "content_categories",
        "content_angles",
        "hook_improvements",
        "posting_schedule",
        "experiments",
        "strategy_gaps",
        mode="before",
    )
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return coerce_str_list(value)


# ---------------------------------------------------------------------------
# Analysis payloads (agent output)
# ---------------------------------------------------------------------------


class PatternAnalysisPayload(BaseModel):
    """Historical pattern recognition across videos."""

    best_performing_categories: list[str] = Field(default_factory=list)
    best_posting_days: list[str] = Field(default_factory=list)
    best_posting_times: list[str] = Field(default_factory=list)
    best_duration: str = ""
    strongest_hooks: list[str] = Field(default_factory=list)
    common_failure_patterns: list[str] = Field(default_factory=list)
    recurring_successful_formats: list[str] = Field(default_factory=list)
    summary: str = ""

    @field_validator(
        "best_performing_categories",
        "best_posting_days",
        "best_posting_times",
        "strongest_hooks",
        "common_failure_patterns",
        "recurring_successful_formats",
        mode="before",
    )
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return coerce_str_list(value)


class TrendReportPayload(BaseModel):
    """Trend report generated from historical analysis."""

    period: str = ""
    patterns: PatternAnalysisPayload
    recommendations: ContentRecommendations
    account_health_score: float = Field(default=0.0, ge=0.0, le=1.0)
    growth_trend: str = ""
    summary: str = ""

    @field_validator("account_health_score", mode="before")
    @classmethod
    def _normalize_health_score(cls, value: Any) -> float:
        return normalize_unit_ratio(value)


class CompetitorAccountData(BaseModel):
    handle: str
    follower_count: int = 0
    posting_frequency: str = ""
    average_views: int = 0
    engagement_rate: float = 0.0
    content_categories: list[str] = Field(default_factory=list)
    posting_schedule: list[str] = Field(default_factory=list)
    recurring_hooks: list[str] = Field(default_factory=list)
    recurring_themes: list[str] = Field(default_factory=list)
    video_styles: list[str] = Field(default_factory=list)
    editing_patterns: list[str] = Field(default_factory=list)
    cta_style: str = ""

    @field_validator(
        "content_categories",
        "posting_schedule",
        "recurring_hooks",
        "recurring_themes",
        "video_styles",
        "editing_patterns",
        mode="before",
    )
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return coerce_str_list(value)


class CompetitorAnalysisPayload(BaseModel):
    """SWOT-style competitor analysis."""

    account: CompetitorAccountData
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)
    content_ideas: list[str] = Field(default_factory=list)
    summary: str = ""

    @field_validator(
        "strengths",
        "weaknesses",
        "opportunities",
        "threats",
        "content_ideas",
        mode="before",
    )
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return coerce_str_list(value)


class ReviewReportPayload(BaseModel):
    """Structured review of Content Creator output — never rewrites content."""

    hook_strength: ScoreWithExplanation
    originality: ScoreWithExplanation
    pacing: ScoreWithExplanation
    emotional_trigger: ScoreWithExplanation
    clarity: ScoreWithExplanation
    audience_alignment: ScoreWithExplanation
    cta: ScoreWithExplanation
    engagement_probability: ScoreWithExplanation
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    approval_recommendation: str = ""

    @field_validator("strengths", "weaknesses", "suggestions", mode="before")
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return coerce_str_list(value)

    @field_validator("confidence_score", mode="before")
    @classmethod
    def _normalize_confidence(cls, value: Any) -> float:
        return normalize_unit_ratio(value)


class CommentAnalysisPayload(BaseModel):
    """Standalone comment analysis for a video."""

    video_id: str
    intelligence: CommentIntelligence
    summary: str = ""


class MetricsSnapshotPayload(BaseModel):
    """Point-in-time metrics snapshot."""

    metric: str
    value: float
    dimension: str | None = None
    context: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# API request/response schemas
# ---------------------------------------------------------------------------


class AnalyzeVideoRequest(BaseModel):
    video_id: str
    content_id: str | None = None


class AnalyzeContentRequest(BaseModel):
    content_id: str | None = None
    content_type: ContentType | None = None


class AnalyzeCompetitorRequest(BaseModel):
    handle: str


class ReviewContentRequest(BaseModel):
    content_id: str
    comment: str | None = None


class ReviewDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REVISION = "request_revision"


class ReviewDecisionRequest(BaseModel):
    decision: ReviewDecision
    comment: str | None = None
    decided_by: str = "user"


class TrendReportRequest(BaseModel):
    period: str = "30d"


class AnalysisRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    version: int
    subject_id: str
    agent: str
    provider: str
    model: str
    prompt_version: str
    payload: dict
    created_at: datetime


class ContentAnalysisRead(AnalysisRead):
    video_id: str


class CompetitorAnalysisRead(AnalysisRead):
    handle: str


class TrendReportRead(AnalysisRead):
    period: str


class ReviewReportRead(AnalysisRead):
    content_id: str
    decision: str | None = None
    decision_comment: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None


class CommentAnalysisRead(AnalysisRead):
    video_id: str


class PatternAnalysisRead(AnalysisRead):
    pass


class MetricsSnapshotRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    metric: str
    value: float
    dimension: str | None = None
    context: dict = Field(default_factory=dict)
    created_at: datetime


class AccountOverview(BaseModel):
    tiktok_handle: str | None = None
    account_configured: bool = False
    #: Set when live TikTok fetch fails; dashboard still loads with manual metrics path.
    live_data_error: str | None = None
    account_health_score: float = 0.0
    total_videos: int = 0
    total_views: int = 0
    avg_engagement_rate: float = 0.0
    recent_videos: list[dict] = Field(default_factory=list)
    best_performers: list[dict] = Field(default_factory=list)
    worst_performers: list[dict] = Field(default_factory=list)
    posting_heatmap: dict = Field(default_factory=dict)
    performance_trends: list[dict] = Field(default_factory=list)
    growth_trends: list[dict] = Field(default_factory=list)


class CompetitorOverview(BaseModel):
    competitors: list[dict] = Field(default_factory=list)
    latest_analyses: list[CompetitorAnalysisRead] = Field(default_factory=list)


class ReviewQueueItem(BaseModel):
    content_id: str
    title: str
    category: str
    status: str
    confidence_score: float
    latest_review: ReviewReportRead | None = None
    created_at: datetime
    updated_at: datetime


class HistoricalAnalytics(BaseModel):
    content_analyses: list[ContentAnalysisRead] = Field(default_factory=list)
    competitor_analyses: list[CompetitorAnalysisRead] = Field(default_factory=list)
    trend_reports: list[TrendReportRead] = Field(default_factory=list)
    review_reports: list[ReviewReportRead] = Field(default_factory=list)
    pattern_analyses: list[PatternAnalysisRead] = Field(default_factory=list)
    metrics_snapshots: list[MetricsSnapshotRead] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    success: bool
    data: dict | None = None
    analysis_id: str | None = None
    version: int | None = None
    error: str | None = None
    error_type: str | None = None
    skipped: bool = False
    skip_reason: str | None = None


class AccountSettingsRead(BaseModel):
    tiktok_handle: str | None = None
    configured: bool = False
    source: str = "none"  # "database" | "environment" | "none"


class AccountSettingsUpdate(BaseModel):
    tiktok_handle: str = Field(min_length=1, max_length=128)

    @field_validator("tiktok_handle")
    @classmethod
    def _normalize_handle(cls, value: str) -> str:
        normalized = normalize_tiktok_handle(value)
        if not normalized:
            raise ValueError("TikTok handle cannot be empty.")
        return normalized


class VideoMetricsData(BaseModel):
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    saves: int | None = None
    reach: int | None = None
    watch_time: float | None = None
    average_watch_duration: float | None = None
    completion_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    profile_visits: int | None = None
    followers_gained: int | None = None
    link_clicks: int | None = None
    user_notes: str | None = None
    publish_date: str | None = None
    publish_time: str | None = None


class VideoMetricsRead(VideoMetricsData):
    video_id: str
    required_complete: bool = False
    missing_required: list[str] = Field(default_factory=list)
    metrics_priority: str = "normal"  # "high" for best/worst performers


class ContentCatalogItem(BaseModel):
    post_id: str = Field(
        validation_alias=AliasChoices("post_id", "video_id"),
        serialization_alias="video_id",
    )
    content_type: ContentType = ContentType.VIDEO
    title: str = ""
    url: str = ""
    caption: str = ""
    publish_date: str = ""
    publish_time: str = ""
    duration: int = 0
    thumbnail: str = ""
    is_analyzed: bool = False
    analysis_version: int | None = None
    analysis_id: str | None = None
    analysis: ContentAnalysisSummary | None = None
    has_media_upload: bool = False
    has_video_upload: bool = False
    upload_filename: str | None = None
    metrics: VideoMetricsRead
    metrics_priority: str = "normal"

    @property
    def video_id(self) -> str:
        return self.post_id


VideoCatalogItem = ContentCatalogItem


class VideoUploadRead(BaseModel):
    video_id: str
    original_filename: str
    mime_type: str
    file_size: int
    uploaded_at: datetime


class MetricsReadiness(BaseModel):
    ready: bool = False
    total_videos: int = 0
    complete_videos: int = 0
    incomplete_videos: list[dict] = Field(default_factory=list)
    required_fields: list[str] = Field(default_factory=list)
    optional_fields: list[str] = Field(default_factory=list)
    optional_recommended_for: list[str] = Field(default_factory=list)


class ContentAnalyticsPage(BaseModel):
    overview: AccountOverview
    readiness: MetricsReadiness
    videos: list[ContentCatalogItem] = Field(default_factory=list)
    required_field_labels: dict[str, str] = Field(default_factory=dict)
    optional_field_labels: dict[str, str] = Field(default_factory=dict)


class AnalyzeAllResponse(BaseModel):
    analyzed: list[AnalysisResponse] = Field(default_factory=list)
    skipped_video_ids: list[str] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)


from .content_analysis import ContentAnalysisSummary  # noqa: E402

ContentCatalogItem.model_rebuild()
