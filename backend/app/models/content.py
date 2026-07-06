"""Pydantic models for the Content Creator agent.

These define the strict JSON contract for generated TikTok content plans. Invalid
LLM output is rejected by validation before it reaches the API or the dashboard.
"""

from __future__ import annotations

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


class ContentResponse(BaseModel):
    """Envelope returned by the ``/content/generate`` endpoint."""

    success: bool
    data: ContentIdea | None = None
    error: str | None = None
    error_type: str | None = None
