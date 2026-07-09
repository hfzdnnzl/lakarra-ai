"""Content Analysis domain model — unified video post-mortem output.

Reusable primitives and sectioned analysis for Content Analyst and future agents
(Strategy, Boardroom, Content Planner, Trend Analyst).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


def _coerce_str_list(value: Any) -> list[str]:
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


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Impact(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CategoricalRating(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    WEAK = "weak"
    POOR = "poor"


class EvidenceSource(str, Enum):
    RETENTION = "retention"
    COMPLETION_RATE = "completion_rate"
    WATCH_DURATION = "watch_duration"
    COMMENTS = "comments"
    SCENE = "scene"
    SCRIPT = "script"
    METRICS = "metrics"


class Evidence(BaseModel):
    source: EvidenceSource
    description: str


class Recommendation(BaseModel):
    text: str
    evidence: list[Evidence] = Field(min_length=1)

    @field_validator("evidence", mode="before")
    @classmethod
    def _coerce_evidence(cls, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]


class RatedDimension(BaseModel):
    rating: CategoricalRating
    score: int = Field(ge=1, le=10)
    confidence: Confidence
    explanation: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)

    @field_validator("strengths", "weaknesses", mode="before")
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return _coerce_str_list(value)


class SceneAnalysis(BaseModel):
    start_timestamp: str
    end_timestamp: str
    purpose: str
    effectiveness: CategoricalRating
    score: int = Field(ge=1, le=10)
    confidence: Confidence
    explanation: str
    recommendations: list[Recommendation] = Field(default_factory=list)


class RootCause(BaseModel):
    factor: str
    estimated_impact: Impact
    confidence: Confidence
    explanation: str
    evidence: list[Evidence] = Field(min_length=1)

    @field_validator("evidence", mode="before")
    @classmethod
    def _coerce_evidence(cls, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]


class ExecutiveSummary(BaseModel):
    overall_verdict: str
    confidence: Confidence
    primary_reason_for_performance: str
    biggest_strength: str
    biggest_weakness: str
    first_priority_action: str


class ContentAnalysisSection(BaseModel):
    hook: RatedDimension
    story_script: RatedDimension
    voiceover: RatedDimension
    scenes: list[SceneAnalysis] = Field(default_factory=list)
    pacing: RatedDimension


class AudienceAnalysisSection(BaseModel):
    retention_summary: str
    strongest_timestamp: str = ""
    weakest_timestamp: str = ""
    drop_off_points: list[str] = Field(default_factory=list)
    comment_sentiment: str = ""
    repeated_questions: list[str] = Field(default_factory=list)
    feature_requests: list[str] = Field(default_factory=list)
    purchase_intent: str = ""
    audience_observations: list[str] = Field(default_factory=list)

    @field_validator(
        "drop_off_points",
        "repeated_questions",
        "feature_requests",
        "audience_observations",
        mode="before",
    )
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return _coerce_str_list(value)


class PerformanceAnalysisSection(BaseModel):
    video: VideoInfo
    metrics: PerformanceMetrics
    engagement: EngagementMetrics
    performance_summary: str


class PerformanceDiagnosisSection(BaseModel):
    root_causes: list[RootCause] = Field(default_factory=list)


class RecommendationsSection(BaseModel):
    immediate_improvements: list[Recommendation] = Field(default_factory=list)
    experiments: list[Recommendation] = Field(default_factory=list)
    future_content_ideas: list[Recommendation] = Field(default_factory=list)


class AnalysisMetadata(BaseModel):
    analysis_version: int = 1
    analysis_mode: Literal["full", "metrics_only"] = "metrics_only"
    video_source: Literal["analytics_upload", "tiktok_download", "none"] = "none"
    linked_content_id: str | None = None
    metrics_provider: str = ""
    metrics_model: str = ""
    metrics_prompt_version: str = ""
    visual_provider: str | None = None
    visual_model: str | None = None
    visual_prompt_version: str | None = None
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class ContentAnalysis(BaseModel):
    """Unified post-mortem analysis of a published TikTok video."""

    executive_summary: ExecutiveSummary
    content_analysis: ContentAnalysisSection
    audience_analysis: AudienceAnalysisSection
    performance_analysis: PerformanceAnalysisSection
    performance_diagnosis: PerformanceDiagnosisSection
    recommendations: RecommendationsSection
    metadata: AnalysisMetadata


# ---------------------------------------------------------------------------
# Pass output models (internal — not returned by API)
# ---------------------------------------------------------------------------


class MetricsPassOutput(BaseModel):
    """Pass 1 LLM output — metrics and audience interpretation."""

    audience_analysis: AudienceAnalysisSection
    content_analysis_partial: ContentAnalysisSection | None = None
    performance_diagnosis: PerformanceDiagnosisSection
    recommendations: RecommendationsSection


class VisualPassOutput(BaseModel):
    """Pass 2 LLM output — visual content analysis."""

    content_analysis: ContentAnalysisSection
    performance_diagnosis: PerformanceDiagnosisSection = Field(
        default_factory=PerformanceDiagnosisSection
    )
    recommendations: RecommendationsSection = Field(
        default_factory=RecommendationsSection
    )


# ---------------------------------------------------------------------------
# Dashboard projection
# ---------------------------------------------------------------------------


class DimensionSummary(BaseModel):
    label: str
    rating: CategoricalRating
    score: int = Field(ge=1, le=10)
    confidence: Confidence
    explanation: str


class VideoAnalysisSummary(BaseModel):
    executive_summary: ExecutiveSummary
    content_ratings: list[DimensionSummary] = Field(default_factory=list)
    scenes: list[SceneAnalysis] = Field(default_factory=list)
    top_root_causes: list[RootCause] = Field(default_factory=list)
    immediate_improvements: list[Recommendation] = Field(default_factory=list)
    experiments: list[Recommendation] = Field(default_factory=list)
    future_content_ideas: list[Recommendation] = Field(default_factory=list)
    performance_summary: str = ""
    analysis_mode: Literal["full", "metrics_only"] = "metrics_only"
    visual_provider: str | None = None


from .analytics import EngagementMetrics, PerformanceMetrics, VideoInfo  # noqa: E402

PerformanceAnalysisSection.model_rebuild()
