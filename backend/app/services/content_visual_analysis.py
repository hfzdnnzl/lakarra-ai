"""Multimodal visual analysis — re-exports from the visual package."""

from __future__ import annotations

from .visual import (
    ContentVisualAnalysisService,
    VideoAnalysisService,
    VisualAnalysisContext,
    build_content_visual_analysis_service,
    build_video_analysis_service,
    parse_review_json,
    resolve_visual_prompt_key,
)
from .visual.backends import VisualBackend, build_visual_backend

# Legacy aliases
build_visual_provider = build_visual_backend
VisualContentProvider = VisualBackend

__all__ = [
    "ContentVisualAnalysisService",
    "VideoAnalysisService",
    "VisualAnalysisContext",
    "VisualBackend",
    "VisualContentProvider",
    "build_content_visual_analysis_service",
    "build_video_analysis_service",
    "build_visual_backend",
    "build_visual_provider",
    "parse_review_json",
    "resolve_visual_prompt_key",
]
