"""Typed primitives for evidence-driven content intelligence."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ConfidenceBand(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    HYPOTHESIS = "hypothesis"


class EvidenceKind(StrEnum):
    METRIC = "metric"
    VISUAL = "visual"
    HISTORICAL = "historical"
    COMPETITOR = "competitor"
    USER_INPUT = "user_input"


class EvidenceRef(BaseModel):
    """A traceable observation used by an intelligence component."""

    id: str
    kind: EvidenceKind
    signal: str
    description: str
    observed_value: float | str | None = None
    baseline_value: float | str | None = None
    source_count: int | None = Field(default=None, ge=0)


class ConfidenceScore(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    band: ConfidenceBand
    rationale: str

    @field_validator("value", mode="before")
    @classmethod
    def normalize_percent(cls, value: Any) -> float:
        numeric = float(value)
        return numeric / 100 if numeric > 1 else numeric


class CausalLink(BaseModel):
    """One step in a measured or hypothesized signal-to-outcome chain."""

    signal: str
    interpretation: str
    behavioral_consequence: str
    outcome: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: ConfidenceScore


class CausalChain(BaseModel):
    links: list[CausalLink] = Field(min_length=1)
    conclusion: str
    confidence: ConfidenceScore


class PriorityScore(BaseModel):
    expected_impact: float = Field(ge=0.0, le=1.0)
    implementation_effort: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    composite: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1)


class IntelligenceRecommendation(BaseModel):
    action: str
    reason: str
    causal_chain: CausalChain
    evidence: list[EvidenceRef] = Field(min_length=1)
    priority: PriorityScore
    expected_metric: str
    measurement_window: str


class ContentDNADimension(BaseModel):
    value: float = Field(ge=0.0, le=100.0)
    confidence: ConfidenceScore
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ContentDNA(BaseModel):
    dimensions: dict[str, ContentDNADimension] = Field(default_factory=dict)


class ContentPattern(BaseModel):
    label: str
    confidence: ConfidenceScore
    evidence: list[EvidenceRef] = Field(default_factory=list)


class KnowledgeContext(BaseModel):
    """Comparable evidence available to a single-content analysis."""

    historical_sample_count: int = Field(default=0, ge=0)
    competitor_sample_count: int = Field(default=0, ge=0)
    historical_patterns: list[str] = Field(default_factory=list)
    competitor_patterns: list[str] = Field(default_factory=list)
    unavailable_signals: list[str] = Field(default_factory=list)


class PerformanceSignal(BaseModel):
    name: str
    value: float | None = None
    unit: str
    available: bool = True
    evidence: EvidenceRef | None = None


class PerformanceSignalSet(BaseModel):
    signals: list[PerformanceSignal] = Field(default_factory=list)
    unavailable_signals: list[str] = Field(default_factory=list)
