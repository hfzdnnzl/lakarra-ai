"""Tests for CAROUSEL content analysis architecture."""

from __future__ import annotations

import json

from app.models.analytics import EngagementMetrics, PerformanceMetrics, PostInfo
from app.models.content_analysis import (
    AudienceAnalysisSection,
    CarouselContentAnalysisSection,
    CarouselMedia,
    CarouselPage,
    CarouselPageAnalysis,
    CategoricalRating,
    Confidence,
    ContentType,
    MediaSource,
    MetricsPassOutput,
    PerformanceAnalysisSection,
    PerformanceDiagnosisSection,
    RatedDimension,
    RecommendationsSection,
    VisualPassOutput,
)
from app.services.analysis_merge import merge_passes, project_content_analysis_summary
from app.services.analytics_mock import build_carousel_visual_pass_response
from app.services.content_merge_specs import CarouselMergeSpec, get_merge_spec
from app.services.media_resolver import CAROUSEL_MANIFEST_MIME
from app.services.visual.backends import MockVisualBackend
from app.services.visual.context import VisualAnalysisContext
from app.services.visual.registry import get_visual_strategy
from app.services.visual.strategies.carousel import CarouselVisualStrategy, extract_carousel_media


def _page(index: int, *, width: int = 1080, height: int = 1350) -> CarouselPage:
    return CarouselPage(
        index=index,
        bytes=f"page-{index}".encode(),
        mime_type="image/jpeg",
        width=width,
        height=height,
    )


def _carousel_media(page_count: int, *, mixed_aspect: bool = False) -> CarouselMedia:
    pages = []
    for i in range(page_count):
        if mixed_aspect and i % 2 == 1:
            pages.append(_page(i, width=1080, height=1920))
        else:
            pages.append(_page(i))
    return CarouselMedia(pages=pages)


def _dimension(score: int = 7) -> RatedDimension:
    return RatedDimension(
        rating=CategoricalRating.GOOD,
        score=score,
        confidence=Confidence.HIGH,
        explanation="test",
    )


def _carousel_metrics_partial(page_count: int) -> CarouselContentAnalysisSection:
    return CarouselContentAnalysisSection(
        cover_slide=_dimension(6),
        page_effectiveness=[
            CarouselPageAnalysis(
                page_index=i,
                composition=_dimension(6),
                typography=_dimension(6),
                readability=_dimension(6),
                branding=_dimension(6),
                color_harmony=_dimension(6),
                whitespace=_dimension(6),
                cta_visibility=_dimension(6),
                emotional_appeal=_dimension(6),
            )
            for i in range(page_count)
        ],
        story_progression=_dimension(6),
        design_consistency=_dimension(6),
        swipe_engagement=_dimension(6),
        cta_effectiveness=_dimension(6),
        overall_flow=_dimension(6),
    )


def _performance() -> PerformanceAnalysisSection:
    return PerformanceAnalysisSection(
        post=PostInfo(post_id="carousel-001", title="Carousel test", content_type=ContentType.CAROUSEL),
        metrics=PerformanceMetrics(views=5000, likes=200, comments=40, shares=30, saves=80),
        engagement=EngagementMetrics(engagement_rate=0.07),
        performance_summary="5000 views, 7% engagement.",
    )


class TestCarouselVisualStrategy:
    def test_three_page_carousel_mock(self):
        media = MediaSource(carousel=_carousel_media(3))
        strategy = CarouselVisualStrategy()
        raw = strategy.analyze(
            media,
            VisualAnalysisContext(review_prompt="carousel visual"),
            MockVisualBackend(),
        )
        payload = VisualPassOutput(**json.loads(raw))
        assert payload.content_analysis.type == "CAROUSEL"
        assert len(payload.content_analysis.page_effectiveness) == 3

    def test_eight_page_carousel_mock(self):
        media = MediaSource(carousel=_carousel_media(8))
        strategy = CarouselVisualStrategy()
        raw = strategy.analyze(media, VisualAnalysisContext(review_prompt="x"), MockVisualBackend())
        payload = VisualPassOutput(**json.loads(raw))
        assert len(payload.content_analysis.page_effectiveness) == 8

    def test_single_page_carousel(self):
        media = MediaSource(carousel=_carousel_media(1))
        extracted = extract_carousel_media(media)
        assert extracted.page_count == 1
        raw = build_carousel_visual_pass_response(1)
        payload = VisualPassOutput(**json.loads(raw))
        assert len(payload.content_analysis.page_effectiveness) == 1

    def test_mixed_aspect_ratios(self):
        media = MediaSource(carousel=_carousel_media(4, mixed_aspect=True))
        carousel = extract_carousel_media(media)
        ratios = [p.aspect_ratio for p in carousel.pages]
        assert ratios[0] != ratios[1]

    def test_registry_resolves_carousel_strategy(self):
        assert isinstance(get_visual_strategy(ContentType.CAROUSEL), CarouselVisualStrategy)


class TestCarouselMerge:
    def test_merge_three_page_carousel(self):
        metrics = MetricsPassOutput(
            audience_analysis=AudienceAnalysisSection(retention_summary="Engagement-led carousel"),
            content_analysis_partial=_carousel_metrics_partial(3),
            performance_diagnosis=PerformanceDiagnosisSection(),
            recommendations=RecommendationsSection(),
        )
        visual = VisualPassOutput(**json.loads(build_carousel_visual_pass_response(3)))
        merged = merge_passes(
            content_type=ContentType.CAROUSEL,
            metrics=metrics,
            visual=visual,
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
        assert merged.metadata.content_type == ContentType.CAROUSEL
        assert merged.content_analysis.type == "CAROUSEL"
        assert merged.content_analysis.cover_slide.score == 8
        assert len(merged.content_analysis.page_effectiveness) == 3

    def test_missing_page_merge(self):
        spec = CarouselMergeSpec()
        metrics_section = _carousel_metrics_partial(3)
        visual_raw = json.loads(build_carousel_visual_pass_response(2))
        visual_section = CarouselContentAnalysisSection(**visual_raw["content_analysis"])
        merged = spec.merge(metrics_section, visual_section, has_visual=True)
        assert len(merged.page_effectiveness) == 3
        assert merged.page_effectiveness[2].page_index == 2

    def test_recommendation_generation(self):
        visual = VisualPassOutput(**json.loads(build_carousel_visual_pass_response(3)))
        merged = merge_passes(
            content_type=ContentType.CAROUSEL,
            metrics=MetricsPassOutput(
                audience_analysis=AudienceAnalysisSection(retention_summary="Carousel engagement"),
                performance_diagnosis=PerformanceDiagnosisSection(),
                recommendations=RecommendationsSection(),
            ),
            visual=visual,
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
        texts = [r.text for r in merged.recommendations.immediate_improvements]
        assert any("cover" in t.lower() for t in texts)
        assert all(r.evidence for r in merged.recommendations.immediate_improvements)

    def test_root_cause_generation(self):
        visual = VisualPassOutput(**json.loads(build_carousel_visual_pass_response(3)))
        merged = merge_passes(
            content_type=ContentType.CAROUSEL,
            metrics=MetricsPassOutput(
                audience_analysis=AudienceAnalysisSection(retention_summary="Carousel engagement"),
                performance_diagnosis=PerformanceDiagnosisSection(),
                recommendations=RecommendationsSection(),
            ),
            visual=visual,
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
        factors = {c.factor.lower() for c in merged.performance_diagnosis.root_causes}
        assert any("cover" in f or "cta" in f or "information" in f for f in factors)
        for cause in merged.performance_diagnosis.root_causes:
            assert cause.evidence
            assert cause.estimated_impact
            assert cause.confidence

    def test_project_summary(self):
        visual = VisualPassOutput(**json.loads(build_carousel_visual_pass_response(3)))
        merged = merge_passes(
            content_type=ContentType.CAROUSEL,
            metrics=MetricsPassOutput(
                audience_analysis=AudienceAnalysisSection(retention_summary="Carousel engagement"),
                performance_diagnosis=PerformanceDiagnosisSection(),
                recommendations=RecommendationsSection(),
            ),
            visual=visual,
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
        assert summary.content_type == ContentType.CAROUSEL
        assert len(summary.content_ratings) == 6
        assert summary.content_ratings[0].label == "Cover slide"

    def test_merge_spec_registry(self):
        assert get_merge_spec(ContentType.CAROUSEL).content_type == ContentType.CAROUSEL


class TestCarouselMediaModel:
    def test_page_order_preserved(self):
        pages = [_page(2), _page(0), _page(1)]
        carousel = CarouselMedia(pages=pages)
        assert [p.index for p in carousel.pages] == [0, 1, 2]

    def test_missing_indices_detection(self):
        carousel = CarouselMedia(pages=[_page(0), _page(2)])
        assert carousel.missing_indices(expected_count=4) == [1, 3]

    def test_carousel_manifest_mime_constant(self):
        assert CAROUSEL_MANIFEST_MIME.startswith("application/")
