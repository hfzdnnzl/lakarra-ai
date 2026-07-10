"""Tests for merging pass outputs into unified ContentAnalysis."""

from __future__ import annotations

from app.models.analytics import EngagementMetrics, PerformanceMetrics, PostInfo
from app.models.content_analysis import (
    AudienceAnalysisSection,
    CategoricalRating,
    Confidence,
    ContentType,
    Evidence,
    EvidenceSource,
    ImageContentAnalysisSection,
    Impact,
    MetricsPassOutput,
    PerformanceAnalysisSection,
    PerformanceDiagnosisSection,
    RatedDimension,
    Recommendation,
    RecommendationsSection,
    RootCause,
    SceneAnalysis,
    VideoContentAnalysisSection,
    VisualPassOutput,
)
from app.services.analysis_merge import merge_passes, project_content_analysis_summary


def _dimension(score: int = 5) -> RatedDimension:
    return RatedDimension(
        rating=CategoricalRating.AVERAGE,
        score=score,
        confidence=Confidence.MEDIUM,
        explanation="test",
    )


def _metrics_pass() -> MetricsPassOutput:
    return MetricsPassOutput(
        audience_analysis=AudienceAnalysisSection(
            retention_summary="Completion 45%",
            drop_off_points=["Mid-video"],
            comment_sentiment="positive",
        ),
        content_analysis_partial=VideoContentAnalysisSection(
            hook=_dimension(4),
            story_script=_dimension(5),
            voiceover=_dimension(5),
            pacing=_dimension(5),
        ),
        performance_diagnosis=PerformanceDiagnosisSection(
            root_causes=[
                RootCause(
                    factor="Weak hook",
                    estimated_impact=Impact.HIGH,
                    confidence=Confidence.MEDIUM,
                    explanation="Early drop-off inferred from completion",
                    evidence=[
                        Evidence(
                            source=EvidenceSource.COMPLETION_RATE,
                            description="Completion 45%",
                        )
                    ],
                )
            ]
        ),
        recommendations=RecommendationsSection(
            immediate_improvements=[
                Recommendation(
                    text="Strengthen opening hook",
                    evidence=[
                        Evidence(
                            source=EvidenceSource.METRICS,
                            description="Low completion rate",
                        )
                    ],
                )
            ],
        ),
    )


def _visual_pass() -> VisualPassOutput:
    return VisualPassOutput(
        content_analysis=VideoContentAnalysisSection(
            hook=RatedDimension(
                rating=CategoricalRating.GOOD,
                score=8,
                confidence=Confidence.HIGH,
                explanation="Strong visual hook at 0:00",
            ),
            story_script=_dimension(7),
            voiceover=_dimension(6),
            pacing=_dimension(7),
            scenes=[
                SceneAnalysis(
                    start_timestamp="0:00",
                    end_timestamp="0:03",
                    purpose="Hook",
                    effectiveness=CategoricalRating.EXCELLENT,
                    score=9,
                    confidence=Confidence.HIGH,
                    explanation="Product close-up",
                )
            ],
        ),
        performance_diagnosis=PerformanceDiagnosisSection(
            root_causes=[
                RootCause(
                    factor="Static frame at 0:08",
                    estimated_impact=Impact.HIGH,
                    confidence=Confidence.HIGH,
                    explanation="No motion mid-video",
                    evidence=[
                        Evidence(
                            source=EvidenceSource.SCENE,
                            description="0:08 — static shot",
                        )
                    ],
                )
            ]
        ),
        recommendations=RecommendationsSection(
            experiments=[
                Recommendation(
                    text="Shorten static scene",
                    evidence=[
                        Evidence(
                            source=EvidenceSource.SCENE,
                            description="0:08 — holds too long",
                        )
                    ],
                )
            ],
        ),
    )


def _image_visual_pass() -> VisualPassOutput:
    return VisualPassOutput(
        content_analysis=ImageContentAnalysisSection(
            composition=_dimension(8),
            typography=_dimension(6),
            visual_hierarchy=_dimension(7),
            branding=_dimension(9),
            message_clarity=_dimension(8),
            call_to_action=_dimension(4),
            visual_appeal=_dimension(7),
            color_harmony=_dimension(9),
            scroll_stopping_potential=_dimension(8),
        ),
    )


def _performance() -> PerformanceAnalysisSection:
    return PerformanceAnalysisSection(
        post=PostInfo(post_id="lk-001", title="Test"),
        metrics=PerformanceMetrics(views=1000, likes=50, comments=10, shares=5, saves=20),
        engagement=EngagementMetrics(engagement_rate=0.085),
        performance_summary="1000 views, 8.5% engagement.",
    )


class TestMergePasses:
    def test_metrics_only_produces_unified_analysis(self):
        merged = merge_passes(
            content_type=ContentType.VIDEO,
            metrics=_metrics_pass(),
            visual=None,
            performance=_performance(),
            analysis_version=1,
            analysis_mode="metrics_only",
            media_source="none",
            linked_content_id=None,
            metrics_provider="mock",
            metrics_model="mock",
            metrics_prompt_version="abc",
        )
        assert merged.metadata.analysis_mode == "metrics_only"
        assert merged.metadata.content_type == ContentType.VIDEO
        assert merged.executive_summary.overall_verdict
        assert merged.content_analysis.hook.score == 4
        assert len(merged.performance_diagnosis.root_causes) == 1

    def test_full_mode_visual_overrides_content_ratings(self):
        merged = merge_passes(
            content_type=ContentType.VIDEO,
            metrics=_metrics_pass(),
            visual=_visual_pass(),
            performance=_performance(),
            analysis_version=1,
            analysis_mode="full",
            media_source="analytics_upload",
            linked_content_id=None,
            metrics_provider="mock",
            metrics_model="mock",
            metrics_prompt_version="abc",
            visual_provider="mock",
            visual_model="mock",
            visual_prompt_version="def",
        )
        assert merged.metadata.analysis_mode == "full"
        assert merged.content_analysis.hook.score == 8
        assert len(merged.content_analysis.scenes) == 1
        assert len(merged.performance_diagnosis.root_causes) == 2
        assert merged.recommendations.experiments

    def test_image_merge(self):
        merged = merge_passes(
            content_type=ContentType.IMAGE,
            metrics=_metrics_pass(),
            visual=_image_visual_pass(),
            performance=_performance(),
            analysis_version=1,
            analysis_mode="full",
            media_source="analytics_upload",
            linked_content_id=None,
            metrics_provider="mock",
            metrics_model="mock",
            metrics_prompt_version="abc",
            visual_provider="mock",
        )
        assert merged.metadata.content_type == ContentType.IMAGE
        assert merged.content_analysis.composition.score == 8

    def test_executive_summary_synthesized(self):
        merged = merge_passes(
            content_type=ContentType.VIDEO,
            metrics=_metrics_pass(),
            visual=_visual_pass(),
            performance=_performance(),
            analysis_version=1,
            analysis_mode="full",
            media_source="analytics_upload",
            linked_content_id=None,
            metrics_provider="mock",
            metrics_model="mock",
            metrics_prompt_version="abc",
            visual_provider="mock",
        )
        assert merged.executive_summary.first_priority_action
        assert merged.executive_summary.biggest_strength
        assert merged.executive_summary.biggest_weakness

    def test_project_content_analysis_summary(self):
        merged = merge_passes(
            content_type=ContentType.VIDEO,
            metrics=_metrics_pass(),
            visual=_visual_pass(),
            performance=_performance(),
            analysis_version=1,
            analysis_mode="full",
            media_source="analytics_upload",
            linked_content_id=None,
            metrics_provider="mock",
            metrics_model="mock",
            metrics_prompt_version="abc",
            visual_provider="mock",
        )
        summary = project_content_analysis_summary(merged)
        assert summary.analysis_mode == "full"
        assert summary.content_type == ContentType.VIDEO
        assert len(summary.content_ratings) == 4
        assert len(summary.top_root_causes) <= 3
