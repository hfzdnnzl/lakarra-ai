"""Database package: declarative base, session factory and schema init."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect

from alembic import command

from .base import Base
from .session import get_db, get_engine, get_session, get_session_factory

__all__ = ["Base", "get_db", "get_engine", "get_session", "get_session_factory", "init_db"]

logger = logging.getLogger("lakarra.database")

_ALEMBIC_CFG = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
# First CMS migration — used to stamp legacy DBs created before Alembic tracking.
_BASELINE_REVISION = "50479057a779"


def init_db() -> None:
    """Ensure the CMS schema exists and is up to date.

    Dev convenience: runs Alembic migrations to ``head``. Legacy SQLite files that
    were bootstrapped via ``create_all`` (no ``alembic_version`` table) are stamped
    at the baseline revision first, then upgraded.
    """

    # Import models so their tables register on ``Base.metadata``.
    from ..models import db as _db  # noqa: F401

    engine = get_engine()
    inspector = inspect(engine)
    if inspector.has_table("contents") and not inspector.has_table("alembic_version"):
        logger.info(
            "Legacy database detected (no alembic_version); stamping %s before upgrade.",
            _BASELINE_REVISION,
        )
        command.stamp(_ALEMBIC_CFG, _BASELINE_REVISION)

    command.upgrade(_ALEMBIC_CFG, "head")
    url = engine.url.render_as_string(hide_password=True)
    logger.info("Database schema ensured (%s).", url)
