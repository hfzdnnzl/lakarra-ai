"""Single-image visual analysis strategy."""

from __future__ import annotations

from ....errors import LLMCallError
from ....models.content_analysis import MediaSource
from ..backends import MockVisualBackend, VisualBackend
from ..context import VisualAnalysisContext
from .base import ContentTypeVisualStrategy

IMAGE_PAGE_DIMENSION_FIELDS: tuple[str, ...] = (
    "composition",
    "typography",
    "readability",
    "branding",
    "color_harmony",
    "whitespace",
    "cta_visibility",
    "emotional_appeal",
)


def extract_image_bytes(media: MediaSource) -> tuple[bytes, str]:
    if media.carousel and media.carousel.pages:
        page = media.carousel.pages[0]
        return page.bytes, page.mime_type
    if media.bytes:
        return media.bytes, media.mime_type or "image/jpeg"
    raise LLMCallError("Image visual analysis requires image bytes.")


class ImageVisualStrategy(ContentTypeVisualStrategy):
    """Visual pass for a single static image."""

    def analyze(
        self,
        media: MediaSource,
        context: VisualAnalysisContext,
        backend: VisualBackend,
    ) -> str:
        if isinstance(backend, MockVisualBackend):
            from ...analytics_mock import build_image_visual_pass_response

            return build_image_visual_pass_response()

        image_bytes, mime_type = extract_image_bytes(media)
        return backend.complete_visual_json(
            context.review_prompt,
            plan_json=context.plan_json,
            images=[(image_bytes, mime_type)],
        )
