"""Build ContentAnalysisInput from catalog data and resolved media."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ...models.content_analysis import ContentAnalysisInput, MediaSource
from ...models.content_types import ContentType
from ...models.db import Content
from ...providers import TikTokVideoData
from ...repositories.analytics_repository import AnalyticsRepository
from ...repositories.content_repository import ContentRepository
from ...services.content_metrics import infer_content_type_from_mime
from ...services.media_resolver import ResolvedMediaSource


def resolve_content_type(
    *,
    post_data: TikTokVideoData,
    content_type_override: ContentType | None = None,
    upload_mime: str | None = None,
    linked_content: Content | None = None,
    resolved_media: ResolvedMediaSource | None = None,
) -> ContentType:
    if content_type_override is not None:
        return content_type_override
    if upload_mime:
        inferred = infer_content_type_from_mime(upload_mime)
        if inferred is not None:
            return inferred
    if resolved_media and resolved_media.content_type:
        return resolved_media.content_type
    if linked_content is not None:
        assets = ContentRepository  # type hint placeholder
        _ = assets
    post_type = getattr(post_data.video, "content_type", None)
    if post_type is not None:
        return post_type
    return ContentType.VIDEO


def build_content_analysis_input(
    session: Session,
    *,
    post_data: TikTokVideoData,
    post_id: str,
    linked_content_id: str | None = None,
    content_type_override: ContentType | None = None,
    historical_context: str = "",
    resolved_media: ResolvedMediaSource | None = None,
) -> ContentAnalysisInput:
    repo = AnalyticsRepository(session)
    uploads = repo.get_video_uploads(post_id)
    upload = uploads[0] if uploads else None
    upload_mime = upload.mime_type if upload else None

    linked_content: Content | None = None
    if linked_content_id:
        linked_content = ContentRepository(session).get(linked_content_id)

    content_type = resolve_content_type(
        post_data=post_data,
        content_type_override=content_type_override,
        upload_mime=upload_mime,
        linked_content=linked_content,
        resolved_media=resolved_media,
    )

    media_source: MediaSource | None = None
    if resolved_media and resolved_media.has_media:
        media_source = MediaSource(
            url=resolved_media.download_url,
            mime_type=resolved_media.mime_type,
            bytes=resolved_media.bytes,
            carousel=resolved_media.carousel,
        )

    return ContentAnalysisInput(
        content_type=content_type,
        post_id=post_id,
        content_metadata=post_data.video,
        performance_data=post_data.performance,
        comments=list(post_data.comments),
        historical_context=historical_context,
        linked_content_id=linked_content_id,
        media_source=media_source,
    )
