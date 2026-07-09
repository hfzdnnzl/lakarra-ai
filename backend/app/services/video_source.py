"""Resolve video bytes for published TikTok analytics (upload first, tikwm fallback)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from ..config import get_settings
from ..providers.tiktok_live import download_tiktok_video
from ..repositories.analytics_repository import AnalyticsRepository
from ..services.storage_service import get_storage

logger = logging.getLogger("lakarra.video_source")

VideoSourceKind = Literal["analytics_upload", "tiktok_download", "none"]


@dataclass
class ResolvedVideoSource:
    bytes: bytes | None
    mime_type: str
    source: VideoSourceKind
    upload_id: str | None
    download_url: str | None = None


def resolve_video_source(
    session: Session,
    *,
    video_id: str,
    tiktok_handle: str,
) -> ResolvedVideoSource:
    """Resolve actual video bytes for multimodal analysis."""

    repo = AnalyticsRepository(session)
    upload = repo.get_video_upload(video_id)
    if upload is not None:
        try:
            raw = get_storage().read_object(upload.storage_key)
        except OSError as exc:
            logger.warning(
                "video_source.upload_read_failed video_id=%s error=%s",
                video_id,
                exc,
            )
        else:
            max_bytes = get_settings().max_upload_bytes
            if len(raw) > max_bytes:
                logger.warning(
                    "video_source.upload_too_large video_id=%s size=%s",
                    video_id,
                    len(raw),
                )
            else:
                return ResolvedVideoSource(
                    bytes=raw,
                    mime_type=upload.mime_type,
                    source="analytics_upload",
                    upload_id=upload.id,
                )

    try:
        downloaded = download_tiktok_video(tiktok_handle, video_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "video_source.tiktok_download_failed video_id=%s error=%s",
            video_id,
            exc,
        )
        downloaded = None

    if downloaded is not None:
        data, mime_type, download_url = downloaded
        return ResolvedVideoSource(
            bytes=data,
            mime_type=mime_type,
            source="tiktok_download",
            upload_id=None,
            download_url=download_url,
        )

    return ResolvedVideoSource(
        bytes=None,
        mime_type="video/mp4",
        source="none",
        upload_id=None,
    )
