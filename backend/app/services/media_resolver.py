"""Resolve media bytes for published TikTok analytics (upload first, remote fallback)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.content_analysis import ContentType
from ..providers.tiktok_live import download_tiktok_image, download_tiktok_video
from ..repositories.analytics_repository import AnalyticsRepository
from ..services.content_metrics import infer_content_type_from_mime
from ..services.storage_service import get_storage

logger = logging.getLogger("lakarra.media_resolver")

MediaSourceKind = Literal["analytics_upload", "remote_download", "none"]


@dataclass
class ResolvedMediaSource:
    bytes: bytes | None
    mime_type: str
    source: MediaSourceKind
    upload_id: str | None
    download_url: str | None = None
    content_type: ContentType | None = None


ResolvedVideoSource = ResolvedMediaSource


def resolve_media_source(
    session: Session,
    *,
    post_id: str,
    tiktok_handle: str,
    content_type: ContentType = ContentType.VIDEO,
) -> ResolvedMediaSource:
    """Resolve actual media bytes for multimodal analysis."""

    repo = AnalyticsRepository(session)
    upload = repo.get_video_upload(post_id)
    if upload is not None:
        try:
            raw = get_storage().read_object(upload.storage_key)
        except OSError as exc:
            logger.warning(
                "media_resolver.upload_read_failed post_id=%s error=%s",
                post_id,
                exc,
            )
        else:
            max_bytes = get_settings().max_upload_bytes
            if len(raw) > max_bytes:
                logger.warning(
                    "media_resolver.upload_too_large post_id=%s size=%s",
                    post_id,
                    len(raw),
                )
            else:
                inferred = infer_content_type_from_mime(upload.mime_type)
                return ResolvedMediaSource(
                    bytes=raw,
                    mime_type=upload.mime_type,
                    source="analytics_upload",
                    upload_id=upload.id,
                    content_type=inferred or content_type,
                )

    if content_type == ContentType.IMAGE:
        try:
            downloaded = download_tiktok_image(tiktok_handle, post_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "media_resolver.tiktok_image_download_failed post_id=%s error=%s",
                post_id,
                exc,
            )
            downloaded = None
    else:
        try:
            downloaded = download_tiktok_video(tiktok_handle, post_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "media_resolver.tiktok_download_failed post_id=%s error=%s",
                post_id,
                exc,
            )
            downloaded = None

    if downloaded is not None:
        data, mime_type, download_url = downloaded
        inferred = infer_content_type_from_mime(mime_type) or content_type
        return ResolvedMediaSource(
            bytes=data,
            mime_type=mime_type,
            source="remote_download",
            upload_id=None,
            download_url=download_url,
            content_type=inferred,
        )

    default_mime = "image/jpeg" if content_type == ContentType.IMAGE else "video/mp4"
    return ResolvedMediaSource(
        bytes=None,
        mime_type=default_mime,
        source="none",
        upload_id=None,
        content_type=content_type,
    )


def resolve_video_source(
    session: Session,
    *,
    video_id: str,
    tiktok_handle: str,
) -> ResolvedMediaSource:
    """Legacy alias — resolves VIDEO media."""

    return resolve_media_source(
        session,
        post_id=video_id,
        tiktok_handle=tiktok_handle,
        content_type=ContentType.VIDEO,
    )
