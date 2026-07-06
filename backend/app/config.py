"""Application configuration.

Settings are loaded from environment variables (and an optional ``.env`` file)
via ``pydantic-settings``. Sensible mock-friendly defaults are provided so the
platform boots with zero external dependencies during Phase 1 development.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General -----------------------------------------------------------
    app_name: str = "Lakarra AI Operating System"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    api_prefix: str = "/api"

    # --- CORS --------------------------------------------------------------
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    # --- Memory / persistence ---------------------------------------------
    # ``in_memory`` keeps everything in process (default, zero-dependency).
    # ``postgres`` uses the SQLAlchemy-backed store (requires a database).
    memory_backend: Literal["in_memory", "postgres"] = "in_memory"
    database_url: str = "postgresql+psycopg2://lakarra:lakarra@localhost:5432/lakarra"

    # --- Cache (optional) --------------------------------------------------
    redis_url: str | None = None

    # --- LLM ---------------------------------------------------------------
    # The provider is abstracted; ``mock`` returns deterministic responses so
    # no API keys are required for local development.
    llm_provider: Literal["mock", "openai", "anthropic", "gemini"] = "mock"
    llm_model: str = "mock-model"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None

    # --- Scheduler ---------------------------------------------------------
    scheduler_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""

    return Settings()
