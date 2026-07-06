"""Database session factory.

The engine is created lazily so the application can boot without a database when
using the in-memory backend (Phase 1 default). Import :func:`get_session` only in
code paths that actually need persistence.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_session() -> Session:
    """Return a new SQLAlchemy session."""

    return get_session_factory()()
