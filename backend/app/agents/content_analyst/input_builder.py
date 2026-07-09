"""Build ContentAnalysisInput from TikTok provider data."""

from __future__ import annotations

from ...models.analytics import VideoInfo
from ...models.content_analysis import ContentAnalysisInput, ContentType, MediaSource
from ...providers import TikTokVideoData
from ...services.media_resolver import resolve_media


def parse_content_type(metadata: VideoInfo) -> ContentType:
    raw = (metadata.content_type or "VIDEO").upper()
    try:
        return ContentType(raw)
    except ValueError as exc:
        from ...errors import InvalidContentTypeError

        raise InvalidContentTypeError(f"Unsupported content type: {raw}") from exc


def build_analysis_input(
    data: TikTokVideoData,
    *,
    historical_context: str = "",
    user_notes: str | None = None,
    media_source: MediaSource | None = None,
) -> ContentAnalysisInput:
    content_type = parse_content_type(data.video)
    resolved = media_source if media_source is not None else resolve_media(data.video)
    return ContentAnalysisInput(
        content_type=content_type,
        content_metadata=data.video,
        performance_data=data.performance,
        comments=list(data.comments),
        historical_context=historical_context,
        user_notes=user_notes,
        media_source=resolved,
    )
