"""Merge metrics and visual pass outputs into unified ContentAnalysis."""

from __future__ import annotations

from datetime import UTC, datetime

from ..models.content_analysis import (
    AnalysisMetadata,
    CategoricalRating,
    Confidence,
    ContentAnalysis,
    ContentAnalysisSectionUnion,
    ContentAnalysisSummary,
    ContentType,
    DimensionSummary,
    ExecutiveSummary,
    ImageContentAnalysisSection,
    Impact,
    MetricsPassOutput,
    PerformanceAnalysisSection,
    PerformanceDiagnosisSection,
    RatedDimension,
    RecommendationsSection,
    RootCause,
    SceneAnalysis,
    VideoContentAnalysisSection,
    VisualPassOutput,
)

_IMPACT_ORDER = {Impact.HIGH: 0, Impact.MEDIUM: 1, Impact.LOW: 2}
_CONFIDENCE_ORDER = {Confidence.HIGH: 0, Confidence.MEDIUM: 1, Confidence.LOW: 2}
_RATING_ORDER = {
    CategoricalRating.EXCELLENT: 0,
    CategoricalRating.GOOD: 1,
    CategoricalRating.AVERAGE: 2,
    CategoricalRating.WEAK: 3,
    CategoricalRating.POOR: 4,
}


def _default_dimension() -> RatedDimension:
    return RatedDimension(
        rating=CategoricalRating.AVERAGE,
        score=5,
        confidence=Confidence.LOW,
        explanation="Insufficient evidence for this dimension.",
        strengths=[],
        weaknesses=[],
        recommendations=[],
    )


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


def _pick_dimension(
    visual: RatedDimension | None,
    metrics: RatedDimension | None,
    *,
    has_visual: bool,
) -> RatedDimension:
    if has_visual and visual is not None:
        return visual
    if metrics is not None:
        return metrics
    return _default_dimension()


def _merge_video_content(
    metrics_partial: VideoContentAnalysisSection | None,
    visual: VideoContentAnalysisSection | None,
    *,
    has_visual: bool,
) -> VideoContentAnalysisSection:
    metrics_partial = metrics_partial or VideoContentAnalysisSection(
        hook=_default_dimension(),
        story_script=_default_dimension(),
        voiceover=_default_dimension(),
        pacing=_default_dimension(),
        scenes=[],
    )
    visual = visual or metrics_partial

    return VideoContentAnalysisSection(
        hook=_pick_dimension(
            visual.hook if has_visual else None,
            metrics_partial.hook,
            has_visual=has_visual,
        ),
        story_script=_pick_dimension(
            visual.story_script if has_visual else None,
            metrics_partial.story_script,
            has_visual=has_visual,
        ),
        voiceover=_pick_dimension(
            visual.voiceover if has_visual else None,
            metrics_partial.voiceover,
            has_visual=has_visual,
        ),
        pacing=_pick_dimension(
            visual.pacing if has_visual else None,
            metrics_partial.pacing,
            has_visual=has_visual,
        ),
        scenes=visual.scenes if has_visual else metrics_partial.scenes,
    )


def _merge_image_content(
    metrics_partial: ImageContentAnalysisSection | None,
    visual: ImageContentAnalysisSection | None,
    *,
    has_visual: bool,
) -> ImageContentAnalysisSection:
    metrics_partial = metrics_partial or ImageContentAnalysisSection(
        composition=_default_dimension(),
        typography=_default_dimension(),
        visual_hierarchy=_default_dimension(),
        branding=_default_dimension(),
        message_clarity=_default_dimension(),
        call_to_action=_default_dimension(),
        visual_appeal=_default_dimension(),
        color_harmony=_default_dimension(),
        scroll_stopping_potential=_default_dimension(),
    )
    visual = visual or metrics_partial

    return ImageContentAnalysisSection(
        composition=_pick_dimension(
            visual.composition if has_visual else None,
            metrics_partial.composition,
            has_visual=has_visual,
        ),
        typography=_pick_dimension(
            visual.typography if has_visual else None,
            metrics_partial.typography,
            has_visual=has_visual,
        ),
        visual_hierarchy=_pick_dimension(
            visual.visual_hierarchy if has_visual else None,
            metrics_partial.visual_hierarchy,
            has_visual=has_visual,
        ),
        branding=_pick_dimension(
            visual.branding if has_visual else None,
            metrics_partial.branding,
            has_visual=has_visual,
        ),
        message_clarity=_pick_dimension(
            visual.message_clarity if has_visual else None,
            metrics_partial.message_clarity,
            has_visual=has_visual,
        ),
        call_to_action=_pick_dimension(
            visual.call_to_action if has_visual else None,
            metrics_partial.call_to_action,
            has_visual=has_visual,
        ),
        visual_appeal=_pick_dimension(
            visual.visual_appeal if has_visual else None,
            metrics_partial.visual_appeal,
            has_visual=has_visual,
        ),
        color_harmony=_pick_dimension(
            visual.color_harmony if has_visual else None,
            metrics_partial.color_harmony,
            has_visual=has_visual,
        ),
        scroll_stopping_potential=_pick_dimension(
            visual.scroll_stopping_potential if has_visual else None,
            metrics_partial.scroll_stopping_potential,
            has_visual=has_visual,
        ),
    )


def _as_video_section(
    section: ContentAnalysisSectionUnion | None,
) -> VideoContentAnalysisSection | None:
    if section is None:
        return None
    if isinstance(section, VideoContentAnalysisSection):
        return section
    return None


def _as_image_section(
    section: ContentAnalysisSectionUnion | None,
) -> ImageContentAnalysisSection | None:
    if section is None:
        return None
    if isinstance(section, ImageContentAnalysisSection):
        return section
    return None


def _merge_content_analysis(
    content_type: ContentType,
    metrics_partial: ContentAnalysisSectionUnion | None,
    visual: ContentAnalysisSectionUnion | None,
    *,
    has_visual: bool,
) -> ContentAnalysisSectionUnion:
    if content_type == ContentType.IMAGE:
        return _merge_image_content(
            _as_image_section(metrics_partial),
            _as_image_section(visual),
            has_visual=has_visual,
        )
    return _merge_video_content(
        _as_video_section(metrics_partial),
        _as_video_section(visual),
        has_visual=has_visual,
    )


def _merge_audience(
    metrics_audience,
    visual: VisualPassOutput | None,
    *,
    has_visual: bool,
    content_type: ContentType,
):
    audience = metrics_audience.model_copy(deep=True)
    if content_type != ContentType.VIDEO:
        return audience
    if has_visual and visual is not None:
        content = _as_video_section(visual.content_analysis)
        if content:
            for scene in content.scenes:
                if scene.score <= 4 and scene.explanation:
                    point = f"{scene.start_timestamp} — {scene.explanation}"
                    if point not in audience.drop_off_points:
                        audience.drop_off_points.append(point)
            if content.scenes:
                best = min(content.scenes, key=lambda s: _RATING_ORDER.get(s.effectiveness, 9))
                worst = max(content.scenes, key=lambda s: _RATING_ORDER.get(s.effectiveness, 0))
                if not audience.strongest_timestamp and best.start_timestamp:
                    audience.strongest_timestamp = best.start_timestamp
                if not audience.weakest_timestamp and worst.start_timestamp:
                    audience.weakest_timestamp = worst.start_timestamp
    return audience


def _dimension_pairs_for_summary(
    content_type: ContentType,
    content: ContentAnalysisSectionUnion,
) -> list[tuple[str, RatedDimension]]:
    if isinstance(content, ImageContentAnalysisSection):
        return [
            ("Composition", content.composition),
            ("Typography", content.typography),
            ("Visual hierarchy", content.visual_hierarchy),
            ("Branding", content.branding),
            ("Message clarity", content.message_clarity),
            ("Call to action", content.call_to_action),
            ("Visual appeal", content.visual_appeal),
            ("Scroll-stop", content.scroll_stopping_potential),
        ]
    if isinstance(content, VideoContentAnalysisSection):
        return [
            ("Hook", content.hook),
            ("Pacing", content.pacing),
            ("Story", content.story_script),
            ("Voiceover", content.voiceover),
        ]
    return []


def _synthesize_executive_summary(
    content_type: ContentType,
    content: ContentAnalysisSectionUnion,
    diagnosis: PerformanceDiagnosisSection,
    recommendations: RecommendationsSection,
    *,
    has_visual: bool,
) -> ExecutiveSummary:
    root_causes = _sort_root_causes(diagnosis.root_causes)
    top_cause = root_causes[0] if root_causes else None

    dimensions = _dimension_pairs_for_summary(content_type, content)
    if not dimensions:
        dimensions = [("content", _default_dimension())]
    best_dim = max(dimensions, key=lambda d: d[1].score)
    worst_dim = min(dimensions, key=lambda d: d[1].score)

    first_action = (
        recommendations.immediate_improvements[0].text
        if recommendations.immediate_improvements
        else "Review performance diagnosis and prioritize the highest-impact fix."
    )

    content_label = "image" if content_type == ContentType.IMAGE else "video"
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
    visual_content = visual.content_analysis if visual else None
    visual_diagnosis = visual.performance_diagnosis if visual else PerformanceDiagnosisSection()
    visual_recs = visual.recommendations if visual else RecommendationsSection()

    content_analysis = _merge_content_analysis(
        content_type,
        metrics.content_analysis_partial,
        visual_content,
        has_visual=has_visual,
    )
    audience_analysis = _merge_audience(
        metrics.audience_analysis,
        visual,
        has_visual=has_visual,
        content_type=content_type,
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

    content = analysis.content_analysis
    ratings = [
        DimensionSummary(
            label=label,
            rating=d.rating,
            score=d.score,
            confidence=d.confidence,
            explanation=d.explanation,
        )
        for label, d in _dimension_pairs_for_summary(analysis.metadata.content_type, content)
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
        analysis_mode=analysis.metadata.analysis_mode,
        visual_provider=visual_provider,
    )


project_video_analysis_summary = project_content_analysis_summary
