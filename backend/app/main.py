"""FastAPI application factory for the Lakarra AI Operating System."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .config import get_settings


def _configure_logging() -> None:
    """Ensure application logs are emitted (works under uvicorn and pytest)."""

    lakarra_logger = logging.getLogger("lakarra")
    lakarra_logger.setLevel(logging.INFO)
    if not logging.getLogger().handlers and not lakarra_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
        lakarra_logger.addHandler(handler)


def create_app() -> FastAPI:
    _configure_logging()
    settings = get_settings()

    if settings.auto_init_db:
        from .database import init_db

        init_db()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Multi-agent AI operating system for the Lakarra business.",
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
