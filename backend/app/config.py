"""Application configuration.

Settings are loaded from environment variables (and an optional ``.env`` file)
via ``pydantic-settings``. Sensible mock-friendly defaults are provided so the
platform boots with zero external dependencies during Phase 1 development.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
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

    # --- Visual content analysis (upload review + analytics pass 2) ---------
    # ``auto`` picks gemini when GEMINI_API_KEY is set, else openai when OPENAI_API_KEY
    # is set, otherwise mock. Set explicitly to mock/gemini/openai to override.
    visual_analysis_provider: Literal["auto", "mock", "gemini", "openai"] = Field(
        default="auto",
        validation_alias=AliasChoices("VISUAL_ANALYSIS_PROVIDER", "VIDEO_ANALYSIS_PROVIDER"),
    )
    visual_analysis_model: str = Field(
        default="gemini-2.0-flash",
        validation_alias=AliasChoices("VISUAL_ANALYSIS_MODEL", "VIDEO_ANALYSIS_MODEL"),
    )
    max_upload_bytes: int = 52_428_800  # 50 MB
    allowed_upload_mime_types: list[str] = Field(
        default_factory=lambda: [
            "video/mp4",
            "video/quicktime",
            "video/webm",
            "image/jpeg",
            "image/png",
            "image/webp",
            "application/vnd.lakarra.carousel+json",
        ]
    )

    # --- TikTok analytics (Content Analyst) --------------------------------
    # Your Lakarra TikTok @handle (without @). Can also be set via the dashboard
    # or PUT /api/analytics/account/settings — the saved value takes precedence.
    tiktok_account_handle: str = ""
    # ``live`` fetches real public TikTok data; ``mock`` is for offline tests only.
    tiktok_provider: Literal["live", "mock"] = "live"
    tiktok_api_base_url: str = "https://www.tikwm.com"
    tiktok_max_videos: int = 35
    tiktok_fetch_timeout_seconds: float = 45.0
    tiktok_cache_ttl_seconds: float = 60.0
    tiktok_rate_limit_retries: int = 3
    tiktok_rate_limit_retry_seconds: float = 1.2

    # --- TikWM API key (paid, with a free tier) ------------------------------
    # When tikwm.com's /api/user/posts is unavailable (returns 403), sign up at
    # https://tikwmapi.com/ for an API key (1000 requests/month on the free tier).
    # When set, the app uses https://tikwmapi.com as the API base and passes the
    # key in the X-TikWMAPI-Key header for all authenticated requests.
    tiktok_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""

    return Settings()


def effective_visual_analysis_provider(
    settings: Settings | None = None,
) -> Literal["mock", "gemini", "openai"]:
    """Resolve which visual analysis backend to use."""

    s = settings or get_settings()
    if s.visual_analysis_provider != "auto":
        return s.visual_analysis_provider
    if s.gemini_api_key:
        return "gemini"
    if s.openai_api_key:
        from .services.ffmpeg_utils import ffmpeg_available

        if ffmpeg_available():
            return "openai"
    return "mock"


def effective_visual_analysis_model(settings: Settings | None = None) -> str:
    """Pick a model name appropriate for the resolved visual analysis provider."""

    s = settings or get_settings()
    provider = effective_visual_analysis_provider(s)
    model = s.visual_analysis_model
    if provider == "openai":
        if model.startswith(("gpt-", "o1", "o3", "o4")):
            return model
        return s.model_name if s.model_name.startswith(("gpt-", "o1", "o3", "o4")) else "gpt-4o"
    if provider == "gemini" and model.startswith("gemini"):
        return model
    if provider == "gemini":
        return "gemini-2.0-flash"
    return model


# Legacy aliases
effective_video_analysis_provider = effective_visual_analysis_provider
effective_video_analysis_model = effective_visual_analysis_model
