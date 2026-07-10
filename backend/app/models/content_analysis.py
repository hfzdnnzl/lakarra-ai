"""Content Analysis domain model — unified VIDEO and IMAGE post-mortem output.

Reusable primitives and sectioned analysis for Content Analyst and future agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, field_validator

from .content_types import ContentType


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


@dataclass
class MediaSource:
    """Reference to analyzable media — bytes for uploads, URL for remote fetch."""

    url: str | None = None
    mime_type: str | None = None
    bytes: bytes | None = None

    def has_media(self) -> bool:
        return bool(self.bytes) or bool(self.url)


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
    COMPOSITION = "composition"
    TYPOGRAPHY = "typography"
    BRANDING = "branding"
    CTA = "cta"


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


class VideoContentAnalysisSection(BaseModel):
    type: Literal["VIDEO"] = "VIDEO"
    hook: RatedDimension
    story_script: RatedDimension
    voiceover: RatedDimension
    scenes: list[SceneAnalysis] = Field(default_factory=list)
    pacing: RatedDimension


class ImageContentAnalysisSection(BaseModel):
    type: Literal["IMAGE"] = "IMAGE"
    composition: RatedDimension
    typography: RatedDimension
    visual_hierarchy: RatedDimension
    branding: RatedDimension
    message_clarity: RatedDimension
    call_to_action: RatedDimension
    visual_appeal: RatedDimension
    color_harmony: RatedDimension
    scroll_stopping_potential: RatedDimension


ContentAnalysisSectionUnion = Annotated[
    Union[VideoContentAnalysisSection, ImageContentAnalysisSection],
    Field(discriminator="type"),
]


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
    post: PostInfo
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
    content_type: ContentType = ContentType.VIDEO
    analysis_mode: Literal["full", "metrics_only"] = "metrics_only"
    media_source: Literal["analytics_upload", "remote_download", "none"] = "none"
    linked_content_id: str | None = None
    providers: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ContentAnalysis(BaseModel):
    """Unified post-mortem analysis of published VIDEO or IMAGE content."""

    executive_summary: ExecutiveSummary
    content_analysis: ContentAnalysisSectionUnion
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
    content_analysis_partial: ContentAnalysisSectionUnion | None = None
    performance_diagnosis: PerformanceDiagnosisSection
    recommendations: RecommendationsSection


class VisualPassOutput(BaseModel):
    """Pass 2 LLM output — visual content analysis."""

    content_analysis: ContentAnalysisSectionUnion
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


class ContentAnalysisSummary(BaseModel):
    content_type: ContentType = ContentType.VIDEO
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


# Backward-compatible alias for existing imports during transition.
VideoAnalysisSummary = ContentAnalysisSummary
ContentAnalysisSection = VideoContentAnalysisSection


@dataclass
class ContentAnalysisInput:
    """Normalized input for the Content Analyst two-pass pipeline."""

    content_type: ContentType
    post_id: str
    content_metadata: PostInfo
    performance_data: PerformanceMetrics
    comments: list[str] = field(default_factory=list)
    historical_context: str = ""
    linked_content_id: str | None = None
    media_source: MediaSource | None = None


from .analytics import EngagementMetrics, PerformanceMetrics, PostInfo  # noqa: E402

PerformanceAnalysisSection.model_rebuild()
