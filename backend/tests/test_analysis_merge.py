"""Tests for merging pass outputs into unified ContentAnalysis."""

from __future__ import annotations

from app.models.analytics import EngagementMetrics, PerformanceMetrics, VideoInfo
from app.models.content_analysis import (
    AudienceAnalysisSection,
    CategoricalRating,
    Confidence,
    ContentAnalysisSection,
    Evidence,
    EvidenceSource,
    Impact,
    MetricsPassOutput,
    PerformanceAnalysisSection,
    PerformanceDiagnosisSection,
    RatedDimension,
    Recommendation,
    RecommendationsSection,
    RootCause,
    SceneAnalysis,
    VisualPassOutput,
)
from app.services.analysis_merge import merge_passes, project_video_analysis_summary


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
        content_analysis_partial=ContentAnalysisSection(
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
        content_analysis=ContentAnalysisSection(
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


def _performance() -> PerformanceAnalysisSection:
    return PerformanceAnalysisSection(
        video=VideoInfo(video_id="lk-001", title="Test"),
        metrics=PerformanceMetrics(views=1000, likes=50, comments=10, shares=5, saves=20),
        engagement=EngagementMetrics(engagement_rate=0.085),
        performance_summary="1000 views, 8.5% engagement.",
    )


class TestMergePasses:
    def test_metrics_only_produces_unified_analysis(self):
        merged = merge_passes(
            _metrics_pass(),
            None,
            _performance(),
            analysis_version=1,
            analysis_mode="metrics_only",
            video_source="none",
            linked_content_id=None,
            metrics_provider="mock",
            metrics_model="mock",
            metrics_prompt_version="abc",
        )
        assert merged.metadata.analysis_mode == "metrics_only"
        assert merged.executive_summary.overall_verdict
        assert merged.content_analysis.hook.score == 4
        assert "visual_review" not in merged.model_dump()
        assert len(merged.performance_diagnosis.root_causes) == 1

    def test_full_mode_visual_overrides_content_ratings(self):
        merged = merge_passes(
            _metrics_pass(),
            _visual_pass(),
            _performance(),
            analysis_version=1,
            analysis_mode="full",
            video_source="analytics_upload",
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

    def test_executive_summary_synthesized(self):
        merged = merge_passes(
            _metrics_pass(),
            _visual_pass(),
            _performance(),
            analysis_version=1,
            analysis_mode="full",
            video_source="analytics_upload",
            linked_content_id=None,
            metrics_provider="mock",
            metrics_model="mock",
            metrics_prompt_version="abc",
            visual_provider="mock",
        )
        assert merged.executive_summary.first_priority_action
        assert merged.executive_summary.biggest_strength
        assert merged.executive_summary.biggest_weakness

    def test_project_video_analysis_summary(self):
        merged = merge_passes(
            _metrics_pass(),
            _visual_pass(),
            _performance(),
            analysis_version=1,
            analysis_mode="full",
            video_source="analytics_upload",
            linked_content_id=None,
            metrics_provider="mock",
            metrics_model="mock",
            metrics_prompt_version="abc",
            visual_provider="mock",
        )
        summary = project_video_analysis_summary(merged)
        assert summary.analysis_mode == "full"
        assert len(summary.content_ratings) == 4
        assert len(summary.top_root_causes) <= 3
