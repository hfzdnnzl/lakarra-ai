"""FastAPI application factory for the Lakarra AI Operating System."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Multi-agent AI operating system for the Lakarra business (Phase 1 scaffold).",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/")
    def root() -> dict:
        return {"name": settings.app_name, "docs": "/docs", "api": settings.api_prefix}

    return app


app = create_app()
