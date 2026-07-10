"""Video visual analysis strategy."""

from __future__ import annotations

from ....errors import LLMCallError
from ....models.content_analysis import MediaSource
from ..backends import MockVisualBackend, VisualBackend
from ..context import VisualAnalysisContext
from .base import ContentTypeVisualStrategy


class VideoVisualStrategy(ContentTypeVisualStrategy):
    """Visual pass for short-form video."""

    def analyze(
        self,
        media: MediaSource,
        context: VisualAnalysisContext,
        backend: VisualBackend,
    ) -> str:
        if isinstance(backend, MockVisualBackend):
            from ...analytics_mock import build_visual_pass_response

            return build_visual_pass_response()

        if not media.bytes:
            raise LLMCallError("Video visual analysis requires video bytes.")

        mime_type = media.mime_type or "video/mp4"
        return backend.complete_visual_json(
            context.review_prompt,
            plan_json=context.plan_json,
            video=(media.bytes, mime_type),
        )
