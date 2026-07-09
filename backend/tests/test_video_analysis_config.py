"""Tests for video analysis provider resolution."""

from __future__ import annotations

import os

import pytest

from app.config import Settings, effective_video_analysis_provider, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_auto_prefers_gemini_when_key_present(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VIDEO_ANALYSIS_PROVIDER", "auto")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings()
    assert effective_video_analysis_provider(settings) == "gemini"


def test_auto_uses_openai_when_only_openai_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VIDEO_ANALYSIS_PROVIDER", "auto")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    settings = Settings()
    assert effective_video_analysis_provider(settings) == "openai"


def test_explicit_mock_stays_mock_even_with_keys(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VIDEO_ANALYSIS_PROVIDER", "mock")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    settings = Settings()
    assert effective_video_analysis_provider(settings) == "mock"


def test_auto_falls_back_to_mock_without_keys(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VIDEO_ANALYSIS_PROVIDER", "auto")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    settings = Settings()
    assert effective_video_analysis_provider(settings) == "mock"
