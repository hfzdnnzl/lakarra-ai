"""Deterministic recommendation ranking for the intelligence pipeline."""

from __future__ import annotations

from collections.abc import Iterable

from ...models.content_intelligence import IntelligenceRecommendation


def _composite(*, impact: float, effort: float, confidence: float) -> float:
    """Favor impact and confidence while making high-effort actions less attractive."""

    return round((impact * 0.5) + (confidence * 0.35) + ((1.0 - effort) * 0.15), 4)


def prioritize_recommendations(
    recommendations: Iterable[IntelligenceRecommendation],
) -> list[IntelligenceRecommendation]:
    """Rank recommendations using explicit factors rather than LLM ordering."""

    ranked = sorted(
        recommendations,
        key=lambda item: (
            _composite(
                impact=item.priority.expected_impact,
                effort=item.priority.implementation_effort,
                confidence=item.priority.confidence,
            ),
            item.priority.expected_impact,
        ),
        reverse=True,
    )

    return [
        item.model_copy(
            update={
                "priority": item.priority.model_copy(
                    update={
                        "composite": _composite(
                            impact=item.priority.expected_impact,
                            effort=item.priority.implementation_effort,
                            confidence=item.priority.confidence,
                        ),
                        "rank": rank,
                    }
                )
            }
        )
        for rank, item in enumerate(ranked, start=1)
    ]
