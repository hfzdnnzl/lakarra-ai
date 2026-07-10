"""Polymorphic merge specs — one implementation per content type."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..models.content_analysis import (
    AudienceAnalysisSection,
    CarouselContentAnalysisSection,
    CarouselPageAnalysis,
    CategoricalRating,
    Confidence,
    ContentAnalysisSectionUnion,
    ImageContentAnalysisSection,
    RatedDimension,
    VideoContentAnalysisSection,
    VisualPassOutput,
)
from ..models.content_types import ContentType as ContentTypeEnum

RATING_ORDER = {
    CategoricalRating.EXCELLENT: 0,
    CategoricalRating.GOOD: 1,
    CategoricalRating.AVERAGE: 2,
    CategoricalRating.WEAK: 3,
    CategoricalRating.POOR: 4,
}


@dataclass(frozen=True)
class DimensionField:
    label: str
    field_name: str


def default_dimension() -> RatedDimension:
    return RatedDimension(
        rating=CategoricalRating.AVERAGE,
        score=5,
        confidence=Confidence.LOW,
        explanation="Insufficient evidence for this dimension.",
        strengths=[],
        weaknesses=[],
        recommendations=[],
    )


def pick_dimension(
    visual: RatedDimension | None,
    metrics: RatedDimension | None,
    *,
    has_visual: bool,
) -> RatedDimension:
    if has_visual and visual is not None:
        return visual
    if metrics is not None:
        return metrics
    return default_dimension()


class ContentMergeSpec(ABC):
    content_type: ContentTypeEnum

    @abstractmethod
    def dimension_fields(self) -> list[DimensionField]:
        """Top-level rated dimensions for executive summary and dashboard."""

    @abstractmethod
    def build_default_section(self) -> ContentAnalysisSectionUnion:
        """Empty section with default dimensions."""

    def merge(
        self,
        metrics_partial: ContentAnalysisSectionUnion | None,
        visual: ContentAnalysisSectionUnion | None,
        *,
        has_visual: bool,
    ) -> ContentAnalysisSectionUnion:
        metrics_partial = metrics_partial or self.build_default_section()
        visual = visual or metrics_partial
        merged_fields: dict[str, RatedDimension] = {}
        for field in self.dimension_fields():
            merged_fields[field.field_name] = pick_dimension(
                getattr(visual, field.field_name, None) if has_visual else None,
                getattr(metrics_partial, field.field_name, None),
                has_visual=has_visual,
            )
        return self._build_section(merged_fields, metrics_partial, visual, has_visual=has_visual)

    @abstractmethod
    def _build_section(
        self,
        merged_fields: dict[str, RatedDimension],
        metrics_partial: ContentAnalysisSectionUnion,
        visual: ContentAnalysisSectionUnion,
        *,
        has_visual: bool,
    ) -> ContentAnalysisSectionUnion:
        ...

    def dimension_pairs_for_summary(
        self, content: ContentAnalysisSectionUnion
    ) -> list[tuple[str, RatedDimension]]:
        pairs: list[tuple[str, RatedDimension]] = []
        for field in self.dimension_fields():
            dim = getattr(content, field.field_name, None)
            if isinstance(dim, RatedDimension):
                pairs.append((field.label, dim))
        return pairs

    def enrich_audience(
        self,
        audience: AudienceAnalysisSection,
        visual: VisualPassOutput | None,
        *,
        has_visual: bool,
    ) -> AudienceAnalysisSection:
        return audience.model_copy(deep=True)

    def content_label(self) -> str:
        return self.content_type.value.lower()


class VideoMergeSpec(ContentMergeSpec):
    content_type = ContentTypeEnum.VIDEO

    def dimension_fields(self) -> list[DimensionField]:
        return [
            DimensionField("Hook", "hook"),
            DimensionField("Pacing", "pacing"),
            DimensionField("Story", "story_script"),
            DimensionField("Voiceover", "voiceover"),
        ]

    def build_default_section(self) -> VideoContentAnalysisSection:
        return VideoContentAnalysisSection(
            hook=default_dimension(),
            story_script=default_dimension(),
            voiceover=default_dimension(),
            pacing=default_dimension(),
            scenes=[],
        )

    def _build_section(
        self,
        merged_fields: dict[str, RatedDimension],
        metrics_partial: ContentAnalysisSectionUnion,
        visual: ContentAnalysisSectionUnion,
        *,
        has_visual: bool,
    ) -> VideoContentAnalysisSection:
        metrics = metrics_partial if isinstance(metrics_partial, VideoContentAnalysisSection) else self.build_default_section()
        vis = visual if isinstance(visual, VideoContentAnalysisSection) else metrics
        return VideoContentAnalysisSection(
            **merged_fields,
            scenes=vis.scenes if has_visual else metrics.scenes,
        )

    def enrich_audience(
        self,
        audience: AudienceAnalysisSection,
        visual: VisualPassOutput | None,
        *,
        has_visual: bool,
    ) -> AudienceAnalysisSection:
        result = audience.model_copy(deep=True)
        if not has_visual or visual is None:
            return result
        content = visual.content_analysis
        if not isinstance(content, VideoContentAnalysisSection):
            return result
        for scene in content.scenes:
            if scene.score <= 4 and scene.explanation:
                point = f"{scene.start_timestamp} — {scene.explanation}"
                if point not in result.drop_off_points:
                    result.drop_off_points.append(point)
        if content.scenes:
            best = min(content.scenes, key=lambda s: RATING_ORDER.get(s.effectiveness, 9))
            worst = max(content.scenes, key=lambda s: RATING_ORDER.get(s.effectiveness, 0))
            if not result.strongest_timestamp and best.start_timestamp:
                result.strongest_timestamp = best.start_timestamp
            if not result.weakest_timestamp and worst.start_timestamp:
                result.weakest_timestamp = worst.start_timestamp
        return result


class ImageMergeSpec(ContentMergeSpec):
    content_type = ContentTypeEnum.IMAGE

    def dimension_fields(self) -> list[DimensionField]:
        return [
            DimensionField("Composition", "composition"),
            DimensionField("Typography", "typography"),
            DimensionField("Visual hierarchy", "visual_hierarchy"),
            DimensionField("Branding", "branding"),
            DimensionField("Message clarity", "message_clarity"),
            DimensionField("Call to action", "call_to_action"),
            DimensionField("Visual appeal", "visual_appeal"),
            DimensionField("Scroll-stop", "scroll_stopping_potential"),
        ]

    def build_default_section(self) -> ImageContentAnalysisSection:
        return ImageContentAnalysisSection(
            composition=default_dimension(),
            typography=default_dimension(),
            visual_hierarchy=default_dimension(),
            branding=default_dimension(),
            message_clarity=default_dimension(),
            call_to_action=default_dimension(),
            visual_appeal=default_dimension(),
            color_harmony=default_dimension(),
            scroll_stopping_potential=default_dimension(),
        )

    def _build_section(
        self,
        merged_fields: dict[str, RatedDimension],
        metrics_partial: ContentAnalysisSectionUnion,
        visual: ContentAnalysisSectionUnion,
        *,
        has_visual: bool,
    ) -> ImageContentAnalysisSection:
        defaults = self.build_default_section()
        base = metrics_partial if isinstance(metrics_partial, ImageContentAnalysisSection) else defaults
        vis = visual if isinstance(visual, ImageContentAnalysisSection) else base
        return ImageContentAnalysisSection(
            **merged_fields,
            color_harmony=pick_dimension(
                vis.color_harmony if has_visual else None,
                base.color_harmony,
                has_visual=has_visual,
            ),
        )


_PAGE_FIELDS: tuple[str, ...] = (
    "composition",
    "typography",
    "readability",
    "branding",
    "color_harmony",
    "whitespace",
    "cta_visibility",
    "emotional_appeal",
)


def _merge_carousel_pages(
    metrics_pages: list[CarouselPageAnalysis],
    visual_pages: list[CarouselPageAnalysis],
    *,
    has_visual: bool,
) -> list[CarouselPageAnalysis]:
    visual_by_index = {page.page_index: page for page in visual_pages}
    metrics_by_index = {page.page_index: page for page in metrics_pages}
    indices = sorted(set(visual_by_index) | set(metrics_by_index))
    merged: list[CarouselPageAnalysis] = []
    for index in indices:
        vis_page = visual_by_index.get(index)
        met_page = metrics_by_index.get(index)
        if vis_page is None and met_page is None:
            continue
        source_vis = vis_page or met_page
        source_met = met_page or vis_page
        assert source_vis is not None and source_met is not None
        page_fields = {
            name: pick_dimension(
                getattr(source_vis, name) if has_visual and vis_page else None,
                getattr(source_met, name),
                has_visual=has_visual and vis_page is not None,
            )
            for name in _PAGE_FIELDS
        }
        merged.append(CarouselPageAnalysis(page_index=index, **page_fields))
    return merged


class CarouselMergeSpec(ContentMergeSpec):
    content_type = ContentTypeEnum.CAROUSEL

    def dimension_fields(self) -> list[DimensionField]:
        return [
            DimensionField("Cover slide", "cover_slide"),
            DimensionField("Story progression", "story_progression"),
            DimensionField("Design consistency", "design_consistency"),
            DimensionField("Swipe engagement", "swipe_engagement"),
            DimensionField("CTA effectiveness", "cta_effectiveness"),
            DimensionField("Overall flow", "overall_flow"),
        ]

    def build_default_section(self) -> CarouselContentAnalysisSection:
        return CarouselContentAnalysisSection(
            cover_slide=default_dimension(),
            page_effectiveness=[],
            story_progression=default_dimension(),
            design_consistency=default_dimension(),
            swipe_engagement=default_dimension(),
            cta_effectiveness=default_dimension(),
            overall_flow=default_dimension(),
        )

    def _build_section(
        self,
        merged_fields: dict[str, RatedDimension],
        metrics_partial: ContentAnalysisSectionUnion,
        visual: ContentAnalysisSectionUnion,
        *,
        has_visual: bool,
    ) -> CarouselContentAnalysisSection:
        defaults = self.build_default_section()
        metrics = (
            metrics_partial
            if isinstance(metrics_partial, CarouselContentAnalysisSection)
            else defaults
        )
        vis = visual if isinstance(visual, CarouselContentAnalysisSection) else metrics
        return CarouselContentAnalysisSection(
            **merged_fields,
            page_effectiveness=_merge_carousel_pages(
                metrics.page_effectiveness,
                vis.page_effectiveness,
                has_visual=has_visual,
            ),
        )


_MERGE_SPECS: dict[ContentTypeEnum, ContentMergeSpec] = {
    ContentTypeEnum.VIDEO: VideoMergeSpec(),
    ContentTypeEnum.IMAGE: ImageMergeSpec(),
    ContentTypeEnum.CAROUSEL: CarouselMergeSpec(),
}


def register_merge_spec(content_type: ContentTypeEnum, spec: ContentMergeSpec) -> None:
    _MERGE_SPECS[content_type] = spec


def get_merge_spec(content_type: ContentTypeEnum) -> ContentMergeSpec:
    try:
        return _MERGE_SPECS[content_type]
    except KeyError as exc:
        raise ValueError(f"No merge spec registered for: {content_type}") from exc
