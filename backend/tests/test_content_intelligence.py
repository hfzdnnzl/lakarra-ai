from app.models.analytics import PerformanceMetrics
from app.models.content_intelligence import (
    CausalChain,
    CausalLink,
    ConfidenceBand,
    ConfidenceScore,
    EvidenceKind,
    EvidenceRef,
    IntelligenceRecommendation,
    PriorityScore,
)
from app.services.content_intelligence import prioritize_recommendations
from app.services.content_intelligence.performance import build_performance_signals


def _recommendation(action: str, impact: float, effort: float, confidence: float):
    evidence = EvidenceRef(
        id=f"metric-{action}",
        kind=EvidenceKind.METRIC,
        signal="completion_rate",
        description="Completion is below the comparable baseline.",
        observed_value=0.2,
        baseline_value=0.4,
        source_count=1,
    )
    score = ConfidenceScore(value=confidence, band=ConfidenceBand.MEDIUM, rationale="Measured")
    chain = CausalChain(
        links=[
            CausalLink(
                signal="low completion",
                interpretation="The opening loses viewers early.",
                behavioral_consequence="Fewer viewers reach the CTA.",
                outcome="Lower conversion opportunity.",
                evidence=[evidence],
                confidence=score,
            )
        ],
        conclusion="Improve the opening before changing the CTA.",
        confidence=score,
    )
    return IntelligenceRecommendation(
        action=action,
        reason="The measured signal is below baseline.",
        causal_chain=chain,
        evidence=[evidence],
        priority=PriorityScore(
            expected_impact=impact,
            implementation_effort=effort,
            confidence=confidence,
            composite=0,
            rank=1,
        ),
        expected_metric="completion_rate",
        measurement_window="next 5 posts",
    )


def test_prioritize_recommendations_uses_explicit_factors():
    low_confidence = _recommendation("Rewrite CTA", impact=0.95, effort=0.95, confidence=0.2)
    strong_action = _recommendation("Strengthen opening", impact=0.8, effort=0.2, confidence=0.9)

    ranked = prioritize_recommendations([low_confidence, strong_action])

    assert [item.action for item in ranked] == ["Strengthen opening", "Rewrite CTA"]
    assert ranked[0].priority.rank == 1
    assert ranked[0].priority.composite > ranked[1].priority.composite


def test_confidence_accepts_percentage_values():
    score = ConfidenceScore(value=85, band=ConfidenceBand.HIGH, rationale="Several signals agree")

    assert score.value == 0.85


def test_performance_signals_keep_unavailable_metrics_explicit():
    signal_set = build_performance_signals(
        PerformanceMetrics(
            views=1000,
            likes=100,
            comments=20,
            shares=10,
            saves=30,
            average_watch_duration=4,
            completion_rate=0.35,
        ),
        duration_seconds=20,
    )

    signals = {signal.name: signal for signal in signal_set.signals}
    assert signals["engagement_rate"].value == 0.16
    assert signals["watch_duration_ratio"].value == 0.2
    assert "link_click_rate" in signal_set.unavailable_signals
    assert "link_click_rate" not in signals
