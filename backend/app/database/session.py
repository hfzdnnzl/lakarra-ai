"""Database engine, session factory and FastAPI dependency.

Works with both SQLite (local development default) and PostgreSQL (AWS RDS in
production) selected via ``DATABASE_URL``.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    url = settings.database_url
    connect_args: dict = {}
    if url.startswith("sqlite"):
        # Allow use across FastAPI's threadpool.
        connect_args["check_same_thread"] = False
    return create_engine(url, pool_pre_ping=True, future=True, connect_args=connect_args)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_session() -> Session:
    """Return a new SQLAlchemy session (caller manages its lifecycle)."""

    return get_session_factory()()


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a session and always closes it."""

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
