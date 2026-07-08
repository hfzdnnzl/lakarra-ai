"""Shared test fixtures.

Uses an isolated in-memory SQLite database per test and overrides the ``get_db``
dependency so API and service tests never touch the local dev database.
"""

from __future__ import annotations

import os

# Configure the app for testing *before* it is imported.
# Force these values (not setdefault): a local .env may set LLM_PROVIDER=openai
# for manual dev, but tests must stay deterministic and offline.
os.environ["AUTO_INIT_DB"] = "false"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["VIDEO_ANALYSIS_PROVIDER"] = "mock"
os.environ["TIKTOK_ACCOUNT_HANDLE"] = "lakarra"

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models.db  # noqa: E402,F401  (register ORM tables on Base.metadata)
from app.database.base import Base  # noqa: E402
from app.database.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

_state: dict = {"factory": None}


def _override_get_db():
    session = _state["factory"]()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _fresh_db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    _state["factory"] = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()
    _state["factory"] = None


@pytest.fixture
def db_session() -> Session:
    session = _state["factory"]()
    try:
        yield session
    finally:
        session.close()
