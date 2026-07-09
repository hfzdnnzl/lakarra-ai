"""Merge metrics and visual analysis passes into a unified ContentAnalysis."""

from __future__ import annotations

from ...models.analytics import ScoreWithExplanation, VideoInfo
from ...models.content_analysis import (
    AnalysisMetadata,
    AnalysisMode,
    ContentAnalysis,
    ContentAnalysisInput,
    ContentType,
    ImageContentAnalysis,
    MetricsPassOutput,
    RatedDimension,
    VideoContentAnalysis,
    VisualPassOutput,
)


def _enrich_score(
    existing: ScoreWithExplanation,
    visual: RatedDimension | None,
) -> ScoreWithExplanation:
    if visual is None:
        return existing
    blended = round((existing.score + visual.score) / 2, 2)
    explanation = f"{existing.explanation} Visual review: {visual.explanation}"
    return ScoreWithExplanation(score=blended, explanation=explanation)


def _merge_video_visual(
    metrics: MetricsPassOutput,
    visual: VideoContentAnalysis,
) -> MetricsPassOutput:
    qs = metrics.quality_scores
    if visual.hook:
        qs.hook_score = _enrich_score(qs.hook_score, visual.hook)
    if visual.pacing:
        qs.pacing_score = _enrich_score(qs.pacing_score, visual.pacing)
    if visual.storytelling:
        qs.storytelling_score = _enrich_score(qs.storytelling_score, visual.storytelling)
    if visual.visual_quality:
        qs.overall_content_health = _enrich_score(qs.overall_content_health, visual.visual_quality)
    return metrics


def _merge_image_visual(
    metrics: MetricsPassOutput,
    visual: ImageContentAnalysis,
) -> MetricsPassOutput:
    qs = metrics.quality_scores
    if visual.visual_appeal:
        qs.emotional_impact = _enrich_score(qs.emotional_impact, visual.visual_appeal)
    if visual.message_clarity:
        qs.educational_value = _enrich_score(qs.educational_value, visual.message_clarity)
    if visual.call_to_action:
        qs.cta_score = _enrich_score(qs.cta_score, visual.call_to_action)
    if visual.scroll_stopping_potential:
        qs.hook_score = _enrich_score(qs.hook_score, visual.scroll_stopping_potential)
    return metrics


def merge_passes(
    *,
    analysis_input: ContentAnalysisInput,
    metrics: MetricsPassOutput,
    visual: VisualPassOutput | None,
    analysis_mode: AnalysisMode,
) -> ContentAnalysis:
    """Combine metrics and optional visual passes based on content type."""

    merged_metrics = metrics
    content_analysis: VideoContentAnalysis | ImageContentAnalysis | None = None

    if visual is not None:
        if analysis_input.content_type == ContentType.VIDEO and visual.video:
            merged_metrics = _merge_video_visual(metrics, visual.video)
            content_analysis = visual.video
        elif analysis_input.content_type == ContentType.IMAGE and visual.image:
            merged_metrics = _merge_image_visual(metrics, visual.image)
            content_analysis = visual.image

    providers: dict[str, str] = {
        "metrics": f"{metrics.provider}/{metrics.model}",
    }
    if visual is not None:
        providers["visual"] = f"{visual.provider}/{visual.model}"

    metadata = AnalysisMetadata(
        content_type=analysis_input.content_type,
        analysis_mode=analysis_mode,
        providers=providers,
    )

    meta: VideoInfo = analysis_input.content_metadata
    return ContentAnalysis(
        content_id=meta.video_id,
        content_metadata=meta,
        performance=analysis_input.performance_data,
        engagement=merged_metrics.engagement,
        quality_scores=merged_metrics.quality_scores,
        retention=merged_metrics.retention,
        comments=merged_metrics.comments,
        content_analysis=content_analysis,
        executive_summary=merged_metrics.executive_summary,
        performance_diagnosis=merged_metrics.performance_diagnosis,
        recommendations=merged_metrics.recommendations,
        metadata=metadata,
    )
