"""Resolve media bytes for published TikTok content visual analysis."""

from __future__ import annotations

import logging

import httpx

from ..models.analytics import VideoInfo
from ..models.content_analysis import ContentType, MediaSource

logger = logging.getLogger("lakarra.media_resolver")

# Minimal valid JPEG header for mock/offline image analysis.
_MOCK_JPEG = bytes(
    [
        0xFF,
        0xD8,
        0xFF,
        0xE0,
        0x00,
        0x10,
        0x4A,
        0x46,
        0x49,
        0x46,
        0x00,
        0x01,
        0x01,
        0x00,
        0x00,
        0x01,
        0x00,
        0x01,
        0x00,
        0x00,
        0xFF,
        0xD9,
    ]
)

# Tiny mock MP4 ftyp box — sufficient for mock visual provider.
_MOCK_MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"


def _parse_content_type(metadata: VideoInfo) -> ContentType:
    raw = getattr(metadata, "content_type", "VIDEO") or "VIDEO"
    try:
        return ContentType(str(raw).upper())
    except ValueError:
        return ContentType.VIDEO


def _mock_bytes(content_type: ContentType) -> tuple[bytes, str]:
    if content_type == ContentType.IMAGE:
        return _MOCK_JPEG, "image/jpeg"
    return _MOCK_MP4, "video/mp4"


def _fetch_url(url: str, timeout: float = 15.0) -> bytes | None:
    if not url or url.startswith("/mock/") or url.startswith("mock://"):
        return None
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            if response.status_code == 200:
                return response.content
    except httpx.HTTPError:
        logger.warning("media_resolver.fetch_failed url=%s", url)
    return None


def resolve_media(metadata: VideoInfo) -> MediaSource | None:
    """Build a ``MediaSource`` with bytes when media can be resolved."""

    content_type = _parse_content_type(metadata)
    url = metadata.url or metadata.thumbnail or None

    if url and not url.startswith("/mock/") and not url.startswith("mock://"):
        fetched = _fetch_url(url)
        if fetched:
            mime = "image/jpeg" if content_type == ContentType.IMAGE else "video/mp4"
            return MediaSource(url=url, mime_type=mime, bytes=fetched)

    # Offline / mock paths — supply deterministic bytes so visual pass can run in tests.
    if url and (url.startswith("/mock/") or url.startswith("mock://")):
        data, mime = _mock_bytes(content_type)
        return MediaSource(url=url, mime_type=mime, bytes=data)

    if content_type == ContentType.IMAGE and metadata.thumbnail:
        data, mime = _mock_bytes(ContentType.IMAGE)
        return MediaSource(url=metadata.thumbnail, mime_type=mime, bytes=data)

    return None
