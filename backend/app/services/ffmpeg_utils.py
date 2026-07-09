"""ffmpeg discovery for video frame extraction."""

from __future__ import annotations

import logging
import shutil

logger = logging.getLogger("lakarra.ffmpeg")


def resolve_ffmpeg_executable() -> str | None:
    """Locate ffmpeg on PATH or via the bundled imageio-ffmpeg wheel."""

    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg
    except ImportError:
        return None
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        logger.warning("ffmpeg.bundled_unavailable")
        return None


def ffmpeg_available() -> bool:
    return resolve_ffmpeg_executable() is not None
