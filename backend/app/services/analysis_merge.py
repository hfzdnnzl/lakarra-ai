"""Merge metrics and visual pass outputs into unified ContentAnalysis."""

from __future__ import annotations

from datetime import UTC, datetime

from ..models.content_analysis import (
    AnalysisInputsSummary,
    AnalysisMetadata,
    CategoricalRating,
    Confidence,
    ContentAnalysis,
    ContentAnalysisSummary,
    ContentType,
    DimensionSummary,
    ExecutiveSummary,
    Impact,
    MetricsPassOutput,
    PerformanceAnalysisSection,
    PerformanceDiagnosisSection,
    RecommendationsSection,
    RootCause,
    SceneAnalysis,
    VideoContentAnalysisSection,
    VisualPassOutput,
)
from .content_merge_specs import default_dimension, get_merge_spec, pick_dimension

# Re-export for tests and specs
_default_dimension = default_dimension
_pick_dimension = pick_dimension

_IMPACT_ORDER = {Impact.HIGH: 0, Impact.MEDIUM: 1, Impact.LOW: 2}
_CONFIDENCE_ORDER = {Confidence.HIGH: 0, Confidence.MEDIUM: 1, Confidence.LOW: 2}

RATING_ORDER = {
    CategoricalRating.EXCELLENT: 0,
    CategoricalRating.GOOD: 1,
    CategoricalRating.AVERAGE: 2,
    CategoricalRating.WEAK: 3,
    CategoricalRating.POOR: 4,
}


def _dedupe_root_causes(causes: list[RootCause]) -> list[RootCause]:
    seen: set[str] = set()
    out: list[RootCause] = []
    for cause in causes:
        key = cause.factor.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(cause)
    return out


def _sort_root_causes(causes: list[RootCause]) -> list[RootCause]:
    return sorted(
        _dedupe_root_causes(causes),
        key=lambda c: (
            _IMPACT_ORDER.get(c.estimated_impact, 9),
            _CONFIDENCE_ORDER.get(c.confidence, 9),
        ),
    )


def _dedupe_recommendations(items: list) -> list:
    seen: set[str] = set()
    out = []
    for item in items:
        key = item.text.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _merge_recommendations(
    metrics: RecommendationsSection,
    visual: RecommendationsSection | None,
) -> RecommendationsSection:
    visual = visual or RecommendationsSection()
    return RecommendationsSection(
        immediate_improvements=_dedupe_recommendations(
            metrics.immediate_improvements + visual.immediate_improvements
        ),
        experiments=_dedupe_recommendations(metrics.experiments + visual.experiments),
        future_content_ideas=_dedupe_recommendations(
            metrics.future_content_ideas + visual.future_content_ideas
        ),
    )


def _synthesize_executive_summary(
    content_type: ContentType,
    content,
    diagnosis: PerformanceDiagnosisSection,
    recommendations: RecommendationsSection,
    *,
    has_visual: bool,
) -> ExecutiveSummary:
    spec = get_merge_spec(content_type)
    root_causes = _sort_root_causes(diagnosis.root_causes)
    top_cause = root_causes[0] if root_causes else None

    dimensions = spec.dimension_pairs_for_summary(content)
    if not dimensions:
        dimensions = [("content", default_dimension())]
    best_dim = max(dimensions, key=lambda d: d[1].score)
    worst_dim = min(dimensions, key=lambda d: d[1].score)

    first_action = (
        recommendations.immediate_improvements[0].text
        if recommendations.immediate_improvements
        else "Review performance diagnosis and prioritize the highest-impact fix."
    )

    content_label = spec.content_label()
    if top_cause:
        verdict = (
            f"This {content_label} {'performed well' if best_dim[1].score >= 7 else 'underperformed'} "
            f"primarily due to {top_cause.factor.lower()}."
        )
        primary_reason = top_cause.explanation
    else:
        verdict = "Performance analysis complete — see diagnosis for drivers."
        primary_reason = "Multiple factors contributed; review root causes for detail."

    confidence = (
        Confidence.HIGH
        if has_visual and top_cause and top_cause.confidence == Confidence.HIGH
        else Confidence.MEDIUM if top_cause else Confidence.LOW
    )

    best_strength = (
        best_dim[1].strengths[0]
        if best_dim[1].strengths
        else f"Strong {best_dim[0].lower()} execution"
    )
    worst_weakness = (
        worst_dim[1].weaknesses[0]
        if worst_dim[1].weaknesses
        else f"{worst_dim[0]} needs improvement"
    )

    return ExecutiveSummary(
        overall_verdict=verdict,
        confidence=confidence,
        primary_reason_for_performance=primary_reason,
        biggest_strength=best_strength,
        biggest_weakness=worst_weakness,
        first_priority_action=first_action,
    )


def merge_passes(
    *,
    content_type: ContentType,
    metrics: MetricsPassOutput,
    visual: VisualPassOutput | None,
    performance: PerformanceAnalysisSection,
    analysis_version: int,
    analysis_mode: str,
    media_source: str,
    linked_content_id: str | None,
    metrics_provider: str,
    metrics_model: str,
    metrics_prompt_version: str,
    visual_provider: str | None = None,
    visual_model: str | None = None,
    visual_prompt_version: str | None = None,
) -> ContentAnalysis:
    """Unify both passes into a single coherent analysis."""

    has_visual = visual is not None
    spec = get_merge_spec(content_type)
    visual_content = visual.content_analysis if visual else None
    visual_diagnosis = visual.performance_diagnosis if visual else PerformanceDiagnosisSection()
    visual_recs = visual.recommendations if visual else RecommendationsSection()

    content_analysis = spec.merge(
        metrics.content_analysis_partial,
        visual_content,
        has_visual=has_visual,
    )
    audience_analysis = spec.enrich_audience(
        metrics.audience_analysis,
        visual,
        has_visual=has_visual,
    )
    performance_diagnosis = PerformanceDiagnosisSection(
        root_causes=_sort_root_causes(
            metrics.performance_diagnosis.root_causes + visual_diagnosis.root_causes
        )
    )
    recommendations = _merge_recommendations(metrics.recommendations, visual_recs)

    executive_summary = _synthesize_executive_summary(
        content_type,
        content_analysis,
        performance_diagnosis,
        recommendations,
        has_visual=has_visual,
    )

    providers: dict[str, str] = {"metrics": metrics_provider}
    if visual_provider:
        providers["visual"] = visual_provider

    metadata = AnalysisMetadata(
        analysis_version=analysis_version,
        content_type=content_type,
        analysis_mode="full" if has_visual else "metrics_only",
        media_source=media_source,  # type: ignore[arg-type]
        linked_content_id=linked_content_id,
        providers=providers,
        generated_at=datetime.now(UTC),
    )

    return ContentAnalysis(
        executive_summary=executive_summary,
        content_analysis=content_analysis,
        audience_analysis=audience_analysis,
        performance_analysis=performance,
        performance_diagnosis=performance_diagnosis,
        recommendations=recommendations,
        metadata=metadata,
    )


def project_content_analysis_summary(analysis: ContentAnalysis) -> ContentAnalysisSummary:
    """Slim projection for dashboard cards."""

    spec = get_merge_spec(analysis.metadata.content_type)
    content = analysis.content_analysis
    ratings = [
        DimensionSummary(
            label=label,
            rating=d.rating,
            score=d.score,
            confidence=d.confidence,
            explanation=d.explanation,
        )
        for label, d in spec.dimension_pairs_for_summary(content)
    ]

    scenes: list[SceneAnalysis] = []
    if isinstance(content, VideoContentAnalysisSection):
        scenes = content.scenes

    visual_provider = analysis.metadata.providers.get("visual")

    return ContentAnalysisSummary(
        content_type=analysis.metadata.content_type,
        executive_summary=analysis.executive_summary,
        content_ratings=ratings,
        scenes=scenes,
        top_root_causes=analysis.performance_diagnosis.root_causes[:3],
        immediate_improvements=analysis.recommendations.immediate_improvements,
        experiments=analysis.recommendations.experiments,
        future_content_ideas=analysis.recommendations.future_content_ideas,
        performance_summary=analysis.performance_analysis.performance_summary,
        analysis_inputs=AnalysisInputsSummary(
            metrics=analysis.performance_analysis.metrics,
            signals=analysis.performance_analysis.signals,
        ),
        analysis_mode=analysis.metadata.analysis_mode,
        visual_provider=visual_provider,
    )


project_video_analysis_summary = project_content_analysis_summary
