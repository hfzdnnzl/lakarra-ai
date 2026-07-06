"""Health and metadata routes."""

from __future__ import annotations

from fastapi import APIRouter

from ...config import get_settings

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
    }
