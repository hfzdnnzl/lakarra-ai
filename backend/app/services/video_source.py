"""Resolve video bytes — legacy re-export. Use media_resolver instead."""

from .media_resolver import (  # noqa: F401
    ResolvedMediaSource,
    ResolvedVideoSource,
    resolve_media_source,
    resolve_video_source,
)
