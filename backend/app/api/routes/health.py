"""Health and metadata routes."""

from __future__ import annotations

from fastapi import APIRouter

from ...config import effective_visual_analysis_provider, get_settings
from ...services.ffmpeg_utils import ffmpeg_available

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "memory_backend": settings.memory_backend,
        "llm_provider": settings.llm_provider,
        "visual_analysis_provider": effective_visual_analysis_provider(settings),
        "video_analysis_provider": effective_visual_analysis_provider(settings),
        "video_analysis_ffmpeg_available": ffmpeg_available(),
    }
