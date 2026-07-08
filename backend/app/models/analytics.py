"""Pydantic models for the Content Analyst agent (Phase 3).

Defines structured analysis contracts for TikTok videos, competitors, trends,
content reviews, and historical analytics. The agent produces these payloads —
it never generates content.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

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
