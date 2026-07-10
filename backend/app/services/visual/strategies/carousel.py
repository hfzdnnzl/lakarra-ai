"""Carousel visual analysis — per-page + whole-carousel in one pass."""

from __future__ import annotations

from ....errors import LLMCallError
from ....models.content_analysis import CarouselMedia, CarouselPage, MediaSource
from ..backends import MockVisualBackend, VisualBackend
from ..context import VisualAnalysisContext
from .base import ContentTypeVisualStrategy
from .image import IMAGE_PAGE_DIMENSION_FIELDS


def extract_carousel_media(media: MediaSource) -> CarouselMedia:
    if media.carousel and media.carousel.pages:
        return media.carousel
    if media.bytes and (media.mime_type or "").startswith("image/"):
        return CarouselMedia(
            pages=[CarouselPage(index=0, bytes=media.bytes, mime_type=media.mime_type or "image/jpeg")]
        )
    raise LLMCallError("Carousel visual analysis requires ordered carousel pages.")


def carousel_images_for_backend(carousel: CarouselMedia) -> list[tuple[bytes, str]]:
    return [(page.bytes, page.mime_type) for page in carousel.pages]


class CarouselVisualStrategy(ContentTypeVisualStrategy):
    """Two-level carousel analysis in a single multimodal call.

    Pass 1 (per-page): composition, typography, readability, branding, etc.
    Pass 2 (whole carousel): cover slide, swipe motivation, narrative, CTA journey.
    """

    PAGE_DIMENSION_FIELDS = IMAGE_PAGE_DIMENSION_FIELDS

    def analyze(
        self,
        media: MediaSource,
        context: VisualAnalysisContext,
        backend: VisualBackend,
    ) -> str:
        carousel = extract_carousel_media(media)

        if isinstance(backend, MockVisualBackend):
            from ...analytics_mock import build_carousel_visual_pass_response

            return build_carousel_visual_pass_response(carousel.page_count)

        images = carousel_images_for_backend(carousel)
        page_manifest = "\n".join(
            f"Slide {page.index + 1}: {page.mime_type}"
            + (f" ({page.width}x{page.height})" if page.width and page.height else "")
            for page in carousel.pages
        )
        prompt = (
            f"{context.review_prompt}\n\n"
            f"Carousel has {carousel.page_count} slides in swipe order:\n{page_manifest}\n"
            "Analyze each slide AND the complete swipe journey."
        )
        return backend.complete_visual_json(
            prompt,
            plan_json=context.plan_json,
            images=images,
        )
