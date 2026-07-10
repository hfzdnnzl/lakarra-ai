"""Content visual analysis service — resolves strategy by content type."""

from __future__ import annotations

from ...models.content_analysis import ContentType, MediaSource
from ...models.content_types import ContentType as ContentTypeEnum
from ..json_utils import extract_json
from .backends import VisualBackend, build_visual_backend
from .context import VisualAnalysisContext
from .registry import get_visual_strategy


class ContentVisualAnalysisService:
    """Routes visual analysis to the correct content-type strategy."""

    def __init__(self, backend: VisualBackend | None = None) -> None:
        self._backend = backend or build_visual_backend()

    def analyze_visual(
        self,
        *,
        content_type: ContentTypeEnum,
        media: MediaSource,
        context: VisualAnalysisContext,
    ) -> str:
        if context.mode != "visual_analysis":
            from .backends import MockVisualBackend

            if isinstance(self._backend, MockVisualBackend):
                return self._backend.complete_legacy_review(context)
            # Fidelity/performance paths are video-only today.
            strategy = get_visual_strategy(ContentType.VIDEO)
            return strategy.analyze(media, context, self._backend)

        strategy = get_visual_strategy(content_type)
        return strategy.analyze(media, context, self._backend)

    def analyze_fidelity(
        self,
        *,
        video_bytes: bytes,
        mime_type: str,
        plan_json: str,
        review_prompt: str,
    ) -> str:
        return self.analyze_visual(
            content_type=ContentTypeEnum.VIDEO,
            media=MediaSource(bytes=video_bytes, mime_type=mime_type),
            context=VisualAnalysisContext(
                review_prompt=review_prompt,
                plan_json=plan_json,
                mode="fidelity",
            ),
        )

    def analyze(
        self,
        *,
        video_bytes: bytes,
        mime_type: str,
        plan_json: str,
        review_prompt: str,
    ) -> str:
        return self.analyze_fidelity(
            video_bytes=video_bytes,
            mime_type=mime_type,
            plan_json=plan_json,
            review_prompt=review_prompt,
        )


def build_content_visual_analysis_service() -> ContentVisualAnalysisService:
    return ContentVisualAnalysisService()


VideoAnalysisService = ContentVisualAnalysisService


def build_video_analysis_service() -> ContentVisualAnalysisService:
    return build_content_visual_analysis_service()


def parse_review_json(text: str) -> dict:
    return extract_json(text)
