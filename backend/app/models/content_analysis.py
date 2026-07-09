"""Content analysis domain models — VIDEO and IMAGE as first-class types.

Reusable primitives (Evidence, RatedDimension, etc.) support both content types.
The unified ``ContentAnalysis`` output is persisted as ``content_analyses.payload``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field

from .analytics import (
    CommentIntelligence,
    ContentRecommendations,
    EngagementMetrics,
    PerformanceMetrics,
    QualityScores,
    RetentionAnalysis,
    VideoInfo,
)


class ContentType(str, Enum):
    VIDEO = "VIDEO"
    IMAGE = "IMAGE"


class AnalysisMode(str, Enum):
    FULL = "full"
    METRICS_ONLY = "metrics_only"


@dataclass
class MediaSource:
    """Reference to analyzable media — bytes for uploads, URL for remote fetch."""

    url: str | None = None
    mime_type: str | None = None
    bytes: bytes | None = None

    def has_media(self) -> bool:
        return bool(self.bytes) or bool(self.url)


@dataclass
class ContentAnalysisInput:
    """Normalized input for the Content Analyst two-pass pipeline."""

    content_type: ContentType
    content_metadata: VideoInfo
    performance_data: PerformanceMetrics
    comments: list[str] = field(default_factory=list)
    historical_context: str = ""
    user_notes: str | None = None
    media_source: MediaSource | None = None


# ---------------------------------------------------------------------------
# Reusable analysis primitives
# ---------------------------------------------------------------------------


class Evidence(BaseModel):
    observation: str
    source: str = ""


class RatedDimension(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    explanation: str
    evidence: list[Evidence] = Field(default_factory=list)


class SceneAnalysis(BaseModel):
    timestamp: str = ""
    description: str = ""
    strength: str = ""


class RootCause(BaseModel):
    issue: str
    evidence: list[Evidence] = Field(default_factory=list)
    severity: str = "medium"


class Recommendation(BaseModel):
    action: str
    rationale: str = ""
    priority: str = "medium"


# ---------------------------------------------------------------------------
# Type-specific visual analysis structures
# ---------------------------------------------------------------------------


class VideoContentAnalysis(BaseModel):
    hook: RatedDimension | None = None
    story_script: str = ""
    voiceover: str = ""
    scenes: list[SceneAnalysis] = Field(default_factory=list)
    pacing: RatedDimension | None = None
    storytelling: RatedDimension | None = None
    visual_quality: RatedDimension | None = None


class ImageContentAnalysis(BaseModel):
    composition: RatedDimension | None = None
    typography: RatedDimension | None = None
    visual_hierarchy: RatedDimension | None = None
    branding: RatedDimension | None = None
    message_clarity: RatedDimension | None = None
    call_to_action: RatedDimension | None = None
    visual_appeal: RatedDimension | None = None
    color_harmony: RatedDimension | None = None
    scroll_stopping_potential: RatedDimension | None = None


# ---------------------------------------------------------------------------
# Pass outputs
# ---------------------------------------------------------------------------


class MetricsPassOutput(BaseModel):
    engagement: EngagementMetrics
    quality_scores: QualityScores
    retention: RetentionAnalysis
    comments: CommentIntelligence
    executive_summary: str = ""
    performance_diagnosis: str = ""
    recommendations: ContentRecommendations = Field(default_factory=ContentRecommendations)
    provider: str = ""
    model: str = ""
    prompt_version: str = ""


class VisualPassOutput(BaseModel):
    content_type: ContentType
    video: VideoContentAnalysis | None = None
    image: ImageContentAnalysis | None = None
    provider: str = ""
    model: str = ""
    prompt_version: str = ""


class AnalysisMetadata(BaseModel):
    content_type: ContentType
    analysis_mode: AnalysisMode
    providers: dict[str, str] = Field(default_factory=dict)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )


class ContentAnalysis(BaseModel):
    """Unified analysis result for VIDEO and IMAGE published content."""

    content_id: str
    content_metadata: VideoInfo
    performance: PerformanceMetrics
    engagement: EngagementMetrics
    quality_scores: QualityScores
    retention: RetentionAnalysis
    comments: CommentIntelligence
    content_analysis: VideoContentAnalysis | ImageContentAnalysis | None = None
    executive_summary: str = ""
    performance_diagnosis: str = ""
    recommendations: ContentRecommendations = Field(default_factory=ContentRecommendations)
    root_causes: list[RootCause] = Field(default_factory=list)
    metadata: AnalysisMetadata

    def to_payload(self) -> dict:
        """Serialize for ``content_analyses.payload`` persistence."""

        data = self.model_dump(mode="json")
        # Legacy dashboard fields (video-keyed) for existing consumers.
        data["video"] = self.content_metadata.model_dump()
        data["summary"] = self.executive_summary
        return data
