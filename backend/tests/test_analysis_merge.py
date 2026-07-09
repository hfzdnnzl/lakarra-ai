"""Tests for merging visual review into metrics-based analysis."""

from __future__ import annotations

from app.models.analytics import (
    CommentIntelligence,
    ContentAnalysisPayload,
    ContentRecommendations,
    EngagementMetrics,
    PerformanceMetrics,
    QualityScores,
    RetentionAnalysis,
    ScoreWithExplanation,
    VideoInfo,
    VisualReviewPayload,
)
from app.services.analysis_merge import merge_visual_into_content_analysis


def _score(value: float, explanation: str) -> ScoreWithExplanation:
    return ScoreWithExplanation(score=value, explanation=explanation)


def _metrics_payload() -> ContentAnalysisPayload:
    return ContentAnalysisPayload(
        video=VideoInfo(video_id="lk-001", title="Test", caption="Test caption"),
        performance=PerformanceMetrics(views=100, likes=5, comments=1, shares=1, saves=0),
        engagement=EngagementMetrics(engagement_rate=0.07),
        quality_scores=QualityScores(
            hook_score=_score(0.4, "text hook"),
            retention_score=_score(0.3, "text retention"),
            cta_score=_score(0.5, "text cta"),
            pacing_score=_score(0.4, "text pacing"),
            storytelling_score=_score(0.4, "text story"),
            emotional_impact=_score(0.5, "text emotion"),
            educational_value=_score(0.5, "text edu"),
            overall_content_health=_score(0.45, "text health"),
        ),
        retention=RetentionAnalysis(
            strongest_timestamp="unknown",
            weakest_timestamp="unknown",
            drop_off_points=["inferred drop"],
            pacing_issues=["slow middle"],
        ),
        comments=CommentIntelligence(),
        summary="Metrics summary only.",
        recommendations=ContentRecommendations(
            hook_improvements=["Try stronger text hook"],
        ),
    )


def _visual_payload() -> VisualReviewPayload:
    return VisualReviewPayload(
        hook_description="Opens with product close-up.",
        scene_breakdown=["0:00 — Hook frame", "0:03 — Reveal"],
        on_screen_text=["Premium invites"],
        pacing_notes="Fast opening cuts.",
        cta_observations="CTA in final frame.",
        hook_score=_score(0.8, "visual hook"),
        retention_score=_score(0.7, "visual retention"),
        pacing_score=_score(0.75, "visual pacing"),
        storytelling_score=_score(0.72, "visual story"),
        strongest_timestamp="0:01",
        weakest_timestamp="0:08",
        drop_off_points=["Static middle shot"],
        summary="Visually strong opener.",
    )


class TestAnalysisMerge:
    def test_metrics_only_when_no_visual(self):
        merged = merge_visual_into_content_analysis(
            _metrics_payload(),
            None,
            analysis_mode="metrics_only",
            video_source="none",
            linked_content_id=None,
        )
        assert merged.analysis_mode == "metrics_only"
        assert merged.visual_review is None
        assert merged.quality_scores.hook_score.score == 0.4

    def test_visual_overrides_scores_and_retention(self):
        merged = merge_visual_into_content_analysis(
            _metrics_payload(),
            _visual_payload(),
            analysis_mode="full",
            video_source="analytics_upload",
            linked_content_id=None,
        )
        assert merged.analysis_mode == "full"
        assert merged.video_source == "analytics_upload"
        assert merged.linked_content_id is None
        assert merged.quality_scores.hook_score.score == 0.8
        assert merged.retention.strongest_timestamp == "0:01"
        assert merged.visual_review is not None
        assert "Opens with product close-up." in merged.summary
        assert "Metrics summary only." in merged.summary
        assert any("visual review" in item.lower() for item in merged.recommendations.hook_improvements)
