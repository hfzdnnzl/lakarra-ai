"""Resolve carousel and other media for analytics."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.content_analysis import CarouselMedia, CarouselPage
from ..models.content_types import ContentType
from ..providers.tiktok_live import (
    download_tiktok_carousel,
    download_tiktok_image,
    download_tiktok_video,
)
from ..repositories.analytics_repository import AnalyticsRepository
from ..services.content_metrics import infer_content_type_from_mime
from ..services.storage_service import get_storage

logger = logging.getLogger("lakarra.media_resolver")

MediaSourceKind = Literal["analytics_upload", "remote_download", "none"]
CAROUSEL_MANIFEST_MIME = "application/vnd.lakarra.carousel+json"


@dataclass
class ResolvedMediaSource:
    bytes: bytes | None
    mime_type: str
    source: MediaSourceKind
    upload_id: str | None
    download_url: str | None = None
    content_type: ContentType | None = None
    carousel: CarouselMedia | None = None

    @property
    def has_media(self) -> bool:
        return bool(self.bytes) or bool(self.carousel and self.carousel.pages)


ResolvedVideoSource = ResolvedMediaSource


def _load_carousel_manifest(raw: bytes) -> CarouselMedia:
    data = json.loads(raw.decode("utf-8"))
    pages: list[CarouselPage] = []
    storage = get_storage()
    for entry in data.get("pages", []):
        index = int(entry["index"])
        storage_key = entry["storage_key"]
        mime_type = entry.get("mime_type", "image/jpeg")
        page_bytes = storage.read_object(storage_key)
        pages.append(
            CarouselPage(
                index=index,
                bytes=page_bytes,
                mime_type=mime_type,
                width=entry.get("width"),
                height=entry.get("height"),
            )
        )
    return CarouselMedia(pages=pages)


def _resolve_upload(
    session: Session,
    *,
    post_id: str,
    content_type: ContentType,
) -> ResolvedMediaSource | None:
    repo = AnalyticsRepository(session)
    uploads = repo.get_video_uploads(post_id)
    upload = uploads[0] if uploads else None
    if upload is None:
        return None
    try:
        raw = get_storage().read_object(upload.storage_key)
    except OSError as exc:
        logger.warning("media_resolver.upload_read_failed post_id=%s error=%s", post_id, exc)
        return None

    max_bytes = get_settings().max_upload_bytes
    if len(raw) > max_bytes:
        logger.warning("media_resolver.upload_too_large post_id=%s size=%s", post_id, len(raw))
        return None

    inferred = infer_content_type_from_mime(upload.mime_type) or content_type

    if upload.mime_type == CAROUSEL_MANIFEST_MIME or inferred == ContentType.CAROUSEL:
        try:
            carousel = _load_carousel_manifest(raw)
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            logger.warning("media_resolver.carousel_manifest_invalid post_id=%s error=%s", post_id, exc)
            return None
        return ResolvedMediaSource(
            bytes=None,
            mime_type=upload.mime_type,
            source="analytics_upload",
            upload_id=upload.id,
            content_type=ContentType.CAROUSEL,
            carousel=carousel,
        )

    return ResolvedMediaSource(
        bytes=raw,
        mime_type=upload.mime_type,
        source="analytics_upload",
        upload_id=upload.id,
        content_type=inferred,
    )


def _resolve_remote(
    *,
    post_id: str,
    tiktok_handle: str,
    content_type: ContentType,
) -> ResolvedMediaSource | None:
    if content_type == ContentType.CAROUSEL:
        try:
            carousel = download_tiktok_carousel(tiktok_handle, post_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "media_resolver.tiktok_carousel_download_failed post_id=%s error=%s",
                post_id,
                exc,
            )
            carousel = None
        if carousel is not None:
            return ResolvedMediaSource(
                bytes=None,
                mime_type=CAROUSEL_MANIFEST_MIME,
                source="remote_download",
                upload_id=None,
                content_type=ContentType.CAROUSEL,
                carousel=carousel,
            )
        return None

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

    if downloaded is None:
        return None

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


def resolve_media_source(
    session: Session,
    *,
    post_id: str,
    tiktok_handle: str,
    content_type: ContentType = ContentType.VIDEO,
) -> ResolvedMediaSource:
    """Resolve actual media bytes for multimodal analysis."""

    uploaded = _resolve_upload(session, post_id=post_id, content_type=content_type)
    if uploaded is not None:
        return uploaded

    remote = _resolve_remote(
        post_id=post_id,
        tiktok_handle=tiktok_handle,
        content_type=content_type,
    )
    if remote is not None:
        return remote

    default_mime = {
        ContentType.IMAGE: "image/jpeg",
        ContentType.CAROUSEL: CAROUSEL_MANIFEST_MIME,
    }.get(content_type, "video/mp4")
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
