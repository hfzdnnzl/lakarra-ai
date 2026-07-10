"""Content Analysis domain model — unified VIDEO and IMAGE post-mortem output.

Reusable primitives and sectioned analysis for Content Analyst and future agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from .content_types import ContentType

__all__ = ["ContentType"]


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
class CarouselPage:
    """Single ordered slide in a carousel — index is zero-based and must be preserved."""

    index: int
    bytes: bytes
    mime_type: str
    width: int | None = None
    height: int | None = None

    @property
    def aspect_ratio(self) -> float | None:
        if self.width and self.height and self.height > 0:
            return round(self.width / self.height, 4)
        return None


@dataclass
class CarouselMedia:
    """Ordered carousel pages — swipe sequence is defined by ascending page index."""

    pages: list[CarouselPage]

    def __post_init__(self) -> None:
        self.pages = sorted(self.pages, key=lambda p: p.index)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def missing_indices(self, expected_count: int | None = None) -> list[int]:
        """Return zero-based indices absent from the page list."""
        if not self.pages:
            return list(range(expected_count or 0))
        upper = expected_count if expected_count is not None else self.pages[-1].index + 1
        present = {page.index for page in self.pages}
        return [idx for idx in range(upper) if idx not in present]


@dataclass
class MediaSource:
    """Reference to analyzable media — bytes, carousel pages, or remote URL."""

    url: str | None = None
    mime_type: str | None = None
    bytes: bytes | None = None
    carousel: CarouselMedia | None = None

    def has_media(self) -> bool:
        if self.carousel and self.carousel.pages:
            return True
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
    CAROUSEL_PAGE = "carousel_page"
    COVER_SLIDE = "cover_slide"
    SWIPE_MOTIVATION = "swipe_motivation"
    NARRATIVE = "narrative"


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


def _coerce_rated_dimension(value: Any) -> Any:
    """Normalize common LLM shorthand into the rich dimension shape."""
    if isinstance(value, RatedDimension):
        return value
    if isinstance(value, str):
        return {
            "rating": CategoricalRating.AVERAGE,
            "score": 5,
            "confidence": Confidence.LOW,
            "explanation": value,
        }
    if isinstance(value, (int, float)):
        score = round(float(value) * 10) if 0 <= value <= 1 else round(float(value))
        return {
            "rating": CategoricalRating.GOOD if score >= 7 else CategoricalRating.AVERAGE,
            "score": max(1, min(10, score)),
            "confidence": Confidence.LOW,
            "explanation": "Score supplied without supporting dimension detail.",
        }
    if isinstance(value, dict):
        normalized = dict(value)
        if "score" in normalized and "rating" not in normalized:
            score = float(normalized["score"])
            if 0 <= score <= 1:
                score = round(score * 10)
            normalized["score"] = max(1, min(10, round(score)))
            normalized["rating"] = (
                CategoricalRating.GOOD if normalized["score"] >= 7 else CategoricalRating.AVERAGE
            )
        normalized.setdefault("confidence", Confidence.LOW)
        normalized.setdefault("explanation", "Dimension detail supplied without an explanation.")
        return normalized
    return value


def _coerce_scene(value: Any) -> Any:
    """Normalize common LLM scene aliases into ``SceneAnalysis`` fields."""
    if isinstance(value, str):
        return {
            "start_timestamp": "",
            "end_timestamp": "",
            "purpose": value,
            "effectiveness": CategoricalRating.AVERAGE,
            "score": 5,
            "confidence": Confidence.LOW,
            "explanation": value,
            "recommendations": [],
        }
    if not isinstance(value, dict):
        return value

    normalized = dict(value)
    normalized.setdefault(
        "start_timestamp",
        normalized.get("start_time", normalized.get("start", "")),
    )
    normalized.setdefault(
        "end_timestamp",
        normalized.get("end_time", normalized.get("end", "")),
    )
    normalized["start_timestamp"] = str(normalized["start_timestamp"])
    normalized["end_timestamp"] = str(normalized["end_timestamp"])
    normalized.setdefault(
        "purpose",
        normalized.get("scene", normalized.get("description", "")),
    )
    purpose = normalized["purpose"]
    if isinstance(purpose, dict):
        normalized["purpose"] = str(
            purpose.get("description")
            or purpose.get("name")
            or purpose.get("text")
            or purpose
        )
    elif isinstance(purpose, list):
        normalized["purpose"] = "; ".join(str(item) for item in purpose)
    elif purpose is None:
        normalized["purpose"] = ""
    elif not isinstance(purpose, str):
        normalized["purpose"] = str(purpose)
    normalized.setdefault("effectiveness", CategoricalRating.AVERAGE)
    normalized.setdefault("score", 5)
    normalized.setdefault("confidence", Confidence.LOW)
    normalized.setdefault(
        "explanation",
        normalized.get("purpose", "Scene detail supplied without an explanation."),
    )
    normalized.setdefault("recommendations", [])
    score = normalized.get("score")
    if isinstance(score, (int, float)) and 0 <= score <= 1:
        normalized["score"] = round(score * 10)
    return normalized


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

    @model_validator(mode="before")
    @classmethod
    def _normalize_dimensions(cls, value: Any) -> Any:
        if isinstance(value, dict):
            value = dict(value)
            for field_name in ("hook", "story_script", "voiceover", "pacing"):
                if field_name in value:
                    value[field_name] = _coerce_rated_dimension(value[field_name])
            if "scenes" in value and isinstance(value["scenes"], list):
                value["scenes"] = [_coerce_scene(scene) for scene in value["scenes"]]
        return value


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

    @model_validator(mode="before")
    @classmethod
    def _normalize_dimensions(cls, value: Any) -> Any:
        if isinstance(value, dict):
            value = dict(value)
            for field_name in (
                "composition",
                "typography",
                "visual_hierarchy",
                "branding",
                "message_clarity",
                "call_to_action",
                "visual_appeal",
                "color_harmony",
                "scroll_stopping_potential",
            ):
                if field_name in value:
                    value[field_name] = _coerce_rated_dimension(value[field_name])
        return value


class CarouselPageAnalysis(BaseModel):
    """Per-slide analysis within a carousel."""

    page_index: int = Field(ge=0)
    composition: RatedDimension
    typography: RatedDimension
    readability: RatedDimension
    branding: RatedDimension
    color_harmony: RatedDimension
    whitespace: RatedDimension
    cta_visibility: RatedDimension
    emotional_appeal: RatedDimension

    @model_validator(mode="before")
    @classmethod
    def _normalize_dimensions(cls, value: Any) -> Any:
        if isinstance(value, dict):
            value = dict(value)
            for field_name in (
                "composition",
                "typography",
                "readability",
                "branding",
                "color_harmony",
                "whitespace",
                "cta_visibility",
                "emotional_appeal",
            ):
                if field_name in value:
                    value[field_name] = _coerce_rated_dimension(value[field_name])
        return value


class CarouselContentAnalysisSection(BaseModel):
    type: Literal["CAROUSEL"] = "CAROUSEL"
    cover_slide: RatedDimension
    page_effectiveness: list[CarouselPageAnalysis] = Field(default_factory=list)
    story_progression: RatedDimension
    design_consistency: RatedDimension
    swipe_engagement: RatedDimension
    cta_effectiveness: RatedDimension
    overall_flow: RatedDimension

    @model_validator(mode="before")
    @classmethod
    def _normalize_dimensions(cls, value: Any) -> Any:
        if isinstance(value, dict):
            value = dict(value)
            for field_name in (
                "cover_slide",
                "story_progression",
                "design_consistency",
                "swipe_engagement",
                "cta_effectiveness",
                "overall_flow",
            ):
                if field_name in value:
                    value[field_name] = _coerce_rated_dimension(value[field_name])
        return value


ContentAnalysisSectionUnion = Annotated[
    Union[
        VideoContentAnalysisSection,
        ImageContentAnalysisSection,
        CarouselContentAnalysisSection,
    ],
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
    """Unified post-mortem analysis of published VIDEO, IMAGE, or CAROUSEL content."""

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
