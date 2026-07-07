"""Database package: declarative base, session factory and schema init."""

from __future__ import annotations

import logging

from .base import Base
from .session import get_db, get_engine, get_session, get_session_factory

__all__ = ["Base", "get_db", "get_engine", "get_session", "get_session_factory", "init_db"]

logger = logging.getLogger("lakarra.database")


def init_db() -> None:
    """Ensure the CMS schema exists.

    Dev convenience: creates tables from the ORM metadata if missing (idempotent).
    In production, run Alembic migrations (``alembic upgrade head``) and set
    ``AUTO_INIT_DB=false``.
    """

    # Import models so their tables register on ``Base.metadata``.
    from ..models import db as _db  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
    url = get_engine().url.render_as_string(hide_password=True)
    logger.info("Database schema ensured (%s).", url)
