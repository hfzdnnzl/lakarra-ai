"""Merge multimodal visual review into metrics-based content analysis."""

from __future__ import annotations

from ..models.analytics import (
    ContentAnalysisPayload,
    ContentRecommendations,
    RetentionAnalysis,
    VisualReviewPayload,
)


def _dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def merge_visual_into_content_analysis(
    metrics_payload: ContentAnalysisPayload,
    visual: VisualReviewPayload | None,
    *,
    analysis_mode: str,
    video_source: str,
    linked_content_id: str | None,
    visual_analysis_provider: str | None = None,
) -> ContentAnalysisPayload:
    """Augment metrics analysis with visual findings when available."""

    payload = metrics_payload.model_copy(deep=True)
    payload.analysis_mode = "full" if visual is not None else "metrics_only"
    payload.video_source = video_source  # type: ignore[assignment]
    payload.linked_content_id = linked_content_id
    payload.visual_review = visual
    payload.visual_analysis_provider = visual_analysis_provider  # type: ignore[assignment]

    if visual is None:
        return payload

    scores = payload.quality_scores
    scores.hook_score = visual.hook_score
    scores.retention_score = visual.retention_score
    scores.pacing_score = visual.pacing_score
    scores.storytelling_score = visual.storytelling_score

    payload.retention = RetentionAnalysis(
        strongest_timestamp=visual.strongest_timestamp or payload.retention.strongest_timestamp,
        weakest_timestamp=visual.weakest_timestamp or payload.retention.weakest_timestamp,
        drop_off_points=_dedupe_strings(
            visual.drop_off_points + payload.retention.drop_off_points
        ),
        pacing_issues=_dedupe_strings(
            ([visual.pacing_notes] if visual.pacing_notes.strip() else [])
            + payload.retention.pacing_issues
        ),
        scene_transition_issues=payload.retention.scene_transition_issues,
    )

    metrics_summary = metrics_payload.summary.strip()
    visual_summary = visual.summary.strip()
    hook_line = visual.hook_description.strip()
    parts = [part for part in (hook_line, visual_summary, metrics_summary) if part]
    payload.summary = " ".join(parts)

    rec = payload.recommendations
    visual_hooks = []
    if visual.hook_description.strip():
        visual_hooks.append(
            f"Strengthen opening based on visual review: {visual.hook_description.strip()}"
        )
    if visual.cta_observations.strip():
        visual_hooks.append(f"CTA on screen: {visual.cta_observations.strip()}")
    payload.recommendations = ContentRecommendations(
        content_categories=rec.content_categories,
        content_angles=rec.content_angles,
        hook_improvements=_dedupe_strings(visual_hooks + rec.hook_improvements),
        posting_schedule=rec.posting_schedule,
        experiments=rec.experiments,
        strategy_gaps=rec.strategy_gaps,
    )
    return payload
