"""Tests for ffmpeg discovery."""

from __future__ import annotations

from app.services.ffmpeg_utils import ffmpeg_available, resolve_ffmpeg_executable


def test_bundled_or_system_ffmpeg_is_available():
    path = resolve_ffmpeg_executable()
    assert path is not None
    assert path.endswith("ffmpeg") or "ffmpeg" in path
    assert ffmpeg_available() is True
