"""Pydantic models for the Content Analyst agent (Phase 3).

Defines structured analysis contracts for TikTok videos, competitors, trends,
content reviews, and historical analytics. The agent produces these payloads —
it never generates content.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


def normalize_tiktok_handle(value: str) -> str:
    """Strip @ and whitespace; lowercase for consistent lookups."""

    return value.strip().lstrip("@").lower()

# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------


class ScoreWithExplanation(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    explanation: str


class VideoInfo(BaseModel):
    video_id: str
    url: str = ""
    title: str = ""
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    publish_date: str = ""
    publish_time: str = ""
    duration: int = 0
    thumbnail: str = ""
    content_category: str = ""


class PerformanceMetrics(BaseModel):
    views: int = 0
    reach: int = 0
    watch_time: float = 0.0
    average_watch_duration: float = 0.0
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    retention_curve: list[float] = Field(default_factory=list)
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


class CommentIntelligence(BaseModel):
    sentiment: str = ""
    repeated_questions: list[str] = Field(default_factory=list)
    feature_requests: list[str] = Field(default_factory=list)
    customer_objections: list[str] = Field(default_factory=list)
    purchase_intent: str = ""
    most_common_keywords: list[str] = Field(default_factory=list)


class ContentRecommendations(BaseModel):
    content_categories: list[str] = Field(default_factory=list)
    content_angles: list[str] = Field(default_factory=list)
    hook_improvements: list[str] = Field(default_factory=list)
    posting_schedule: list[str] = Field(default_factory=list)
    experiments: list[str] = Field(default_factory=list)
    strategy_gaps: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Analysis payloads (agent output)
# ---------------------------------------------------------------------------


class ContentAnalysisPayload(BaseModel):
    """Full analysis of a published Lakarra TikTok video."""

    video: VideoInfo
    performance: PerformanceMetrics
    engagement: EngagementMetrics
    quality_scores: QualityScores
    retention: RetentionAnalysis
    comments: CommentIntelligence
    summary: str
    recommendations: ContentRecommendations = Field(default_factory=ContentRecommendations)


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


class TrendReportPayload(BaseModel):
    """Trend report generated from historical analysis."""

    period: str = ""
    patterns: PatternAnalysisPayload
    recommendations: ContentRecommendations
    account_health_score: float = Field(default=0.0, ge=0.0, le=1.0)
    growth_trend: str = ""
    summary: str = ""


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


class CompetitorAnalysisPayload(BaseModel):
    """SWOT-style competitor analysis."""

    account: CompetitorAccountData
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)
    content_ideas: list[str] = Field(default_factory=list)
    summary: str = ""


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


class VideoMetricsRead(VideoMetricsData):
    video_id: str
    required_complete: bool = False
    missing_required: list[str] = Field(default_factory=list)
    metrics_priority: str = "normal"  # "high" for best/worst performers


class VideoCatalogItem(BaseModel):
    video_id: str
    title: str
    url: str = ""
    caption: str = ""
    publish_date: str = ""
    duration: int = 0
    thumbnail: str = ""
    is_analyzed: bool = False
    analysis_version: int | None = None
    analysis_id: str | None = None
    analysis_summary: str | None = None
    metrics: VideoMetricsRead
    metrics_priority: str = "normal"


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
    videos: list[VideoCatalogItem] = Field(default_factory=list)
    required_field_labels: dict[str, str] = Field(default_factory=dict)
    optional_field_labels: dict[str, str] = Field(default_factory=dict)


class AnalyzeAllResponse(BaseModel):
    analyzed: list[AnalysisResponse] = Field(default_factory=list)
    skipped_video_ids: list[str] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)
