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
    # ``in_memory`` keeps the multi-agent shared memory in process (default).
    # ``postgres`` uses the SQLAlchemy-backed store (requires a database).
    memory_backend: Literal["in_memory", "postgres"] = "in_memory"

    # Content Management System database (SQLAlchemy). Defaults to a local SQLite
    # file so the CMS works with zero setup; point DATABASE_URL at AWS RDS
    # PostgreSQL in production (e.g. postgresql+psycopg2://user:pass@host:5432/db).
    database_url: str = "sqlite:///./lakarra.db"
    # Ensure the CMS schema exists on startup (dev convenience). In production run
    # Alembic migrations instead and set this to false.
    auto_init_db: bool = True

    # --- Object storage (AWS S3 compatible) --------------------------------
    # ``local`` writes to the filesystem (dev); ``s3`` uses AWS S3 via boto3.
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_dir: str = "./storage"
    s3_bucket: str | None = None
    s3_region: str | None = None
    # Optional custom endpoint (e.g. LocalStack / MinIO).
    s3_endpoint_url: str | None = None

    # --- Cache (optional) --------------------------------------------------
    redis_url: str | None = None

    # --- LLM ---------------------------------------------------------------
    # The provider is abstracted; ``mock`` returns deterministic responses so
    # no API keys are required for local development.
    llm_provider: Literal["mock", "openai", "anthropic", "gemini"] = "mock"
    llm_model: str = "mock-model"
    # Model name for real providers (e.g. OpenAI). Read from MODEL_NAME.
    model_name: str = Field(default="gpt-4o-mini", validation_alias="MODEL_NAME")
    llm_timeout_seconds: float = 30.0
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None

    # --- Scheduler ---------------------------------------------------------
    scheduler_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""

    return Settings()
