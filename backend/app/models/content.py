"""Pydantic models for the Content Creator agent.

These define the strict JSON contract for generated TikTok content plans. Invalid
LLM output is rejected by validation before it reaches the API or the dashboard.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ContentCategory(str, Enum):
    AESTHETIC = "aesthetic"
    EDUCATIONAL = "educational"
    PRODUCT_COMPARISON = "product_comparison"
    POV = "pov"
    TESTIMONIAL = "testimonial"
    STORYTELLING = "storytelling"
    BEHIND_THE_SCENES = "behind_the_scenes"
    TREND_ADAPTATION = "trend_adaptation"


class ContentStatus(str, Enum):
    """Content lifecycle states (DRAFT -> ... -> ARCHIVED)."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    FILMING = "filming"
    EDITING = "editing"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    ANALYZED = "analyzed"
    PROMOTED = "promoted"
    ARCHIVED = "archived"


class TimelineScene(BaseModel):
    """A single time-boxed scene in the content timeline."""

    model_config = {"extra": "forbid"}

    start: int = Field(ge=0, description="Scene start time in seconds.")
    end: int = Field(gt=0, description="Scene end time in seconds.")
    scene: str = Field(min_length=1, description="What happens on screen.")
    camera: str = Field(default="", description="Camera direction / shot type.")
    text: str = Field(default="", description="On-screen text.")
    voiceover: str | None = Field(default=None, description="Optional voiceover line.")
    sound_effect: str | None = Field(default=None, description="Optional sound effect.")

    @model_validator(mode="after")
    def _check_bounds(self) -> TimelineScene:
        if self.end <= self.start:
            raise ValueError(f"Scene end ({self.end}) must be greater than start ({self.start}).")
        if self.voiceover is not None and not self.voiceover.strip():
            self.voiceover = None
        if self.sound_effect is not None and not self.sound_effect.strip():
            self.sound_effect = None
        return self


class ContentIdea(BaseModel):
    """A complete, validated TikTok content plan."""

    model_config = {"use_enum_values": True}

    title: str = Field(min_length=1)
    category: ContentCategory
    target_audience: str = Field(min_length=1)
    hook: str = Field(min_length=1)
    duration: int = Field(gt=0, le=180, description="Total duration in seconds.")
    timeline: list[TimelineScene] = Field(min_length=1)
    music_suggestion: str | None = None
    caption: str = Field(min_length=1)
    hashtags: list[str] = Field(default_factory=list)
    cta: str = Field(min_length=1)
    posting_time: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_timeline(self) -> ContentIdea:
        # Scenes must be non-overlapping and ordered by start time.
        last_end = 0
        for scene in self.timeline:
            if scene.start < last_end:
                raise ValueError("Timeline scenes must be ordered and non-overlapping.")
            last_end = scene.end
        # The timeline should cover the full declared duration.
        if last_end > self.duration:
            raise ValueError(
                f"Timeline extends to {last_end}s beyond declared duration {self.duration}s."
            )
        return self


class ContentRequest(BaseModel):
    """Input brief for a content generation request."""

    business_goal: str = Field(min_length=1)
    target_audience: str = ""
    product: str = "Digital Wedding Invitation"
    constraints: list[str] = Field(default_factory=list)


class GenerateRequest(ContentRequest):
    """Generation request that may target an existing content item (regeneration)."""

    #: When set, a new version is created on the existing content item.
    content_id: str | None = None
    temperature: float = 0.7


class ContentResponse(BaseModel):
    """Envelope returned by the ``/content/generate`` endpoint."""

    success: bool
    data: ContentIdea | None = None
    content_id: str | None = None
    error: str | None = None
    error_type: str | None = None


# ---------------------------------------------------------------------------
# CMS read/request schemas (Phase 2.5)
# ---------------------------------------------------------------------------


class ContentSceneRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    sequence_number: int
    start_time: int
    end_time: int
    scene_description: str
    camera_direction: str
    on_screen_text: str
    voiceover: str | None = None
    sound_effect: str | None = None


class ContentSummary(BaseModel):
    """Compact representation used in the Content Library list."""

    model_config = {"from_attributes": True}

    id: str
    title: str
    category: str
    status: str
    confidence_score: float
    created_at: datetime
    updated_at: datetime


class ContentRead(BaseModel):
    """Full content record used by the detail page."""

    model_config = {"from_attributes": True}

    id: str
    title: str
    category: str
    business_goal: str
    target_audience: str
    product: str
    constraints: list[str] = Field(default_factory=list)
    performance_notes: str | None = None
    tiktok_video_id: str | None = None
    hook: str
    duration: int
    caption: str
    hashtags: list[str]
    cta: str
    posting_time: str
    confidence_score: float
    music_suggestion: str | None = None
    status: str
    active_version: int
    created_at: datetime
    updated_at: datetime
    scenes: list[ContentSceneRead] = Field(default_factory=list)


class ContentVersionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    version_number: int
    hook: str
    is_active: bool
    created_at: datetime
    snapshot: dict = Field(default_factory=dict)


class FeedbackRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    message: str
    created_by: str
    created_at: datetime


class StatusHistoryRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    old_status: str | None
    new_status: str
    changed_by: str
    changed_at: datetime
    comment: str | None = None


class GenerationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    model_used: str
    prompt_version: str
    temperature: float
    token_usage: dict
    generation_time: float
    created_at: datetime


class PaginatedContents(BaseModel):
    items: list[ContentSummary]
    total: int
    page: int
    page_size: int
    pages: int


class StatusUpdateRequest(BaseModel):
    status: ContentStatus
    changed_by: str = "user"
    comment: str | None = None


class FeedbackRequest(BaseModel):
    message: str = Field(min_length=1)
    created_by: str = "user"


class PerformanceNotesRequest(BaseModel):
    performance_notes: str = Field(default="")


class ContentAssetRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    content_id: str
    mime_type: str
    file_size: int
    original_filename: str
    created_at: datetime


class FidelityReviewPayload(BaseModel):
    """Structured plan-fidelity review from the Content Creator agent."""

    overall_match_score: float = Field(ge=0.0, le=1.0)
    hook_match: str
    scene_notes: list[str] = Field(default_factory=list)
    voiceover_usage: str
    cta_present: bool
    suggestions: list[str] = Field(default_factory=list)
    summary: str


class PerformanceReviewPayload(BaseModel):
    """Structured performance outlook from the Content Analyst agent."""

    hook_strength: float = Field(ge=0.0, le=1.0)
    emotional_triggers: list[str] = Field(default_factory=list)
    pattern_match: str
    compared_to_past_posts: list[str] = Field(default_factory=list)
    posting_recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str


class ContentReviewRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    content_id: str
    asset_id: str | None
    review_type: str
    agent: str
    payload: dict
    created_at: datetime


class ReviewResponse(BaseModel):
    success: bool
    fidelity: FidelityReviewPayload | None = None
    performance: PerformanceReviewPayload | None = None
    error: str | None = None
    error_type: str | None = None
