"""Integration tests for live TikTok data fetching (requires network)."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.providers.tiktok_live import LiveTikTokProvider


@pytest.mark.integration
def test_live_tiktok_fetches_real_account(monkeypatch):
    monkeypatch.setenv("TIKTOK_PROVIDER", "live")
    get_settings.cache_clear()
    provider = LiveTikTokProvider("charlidamelio")
    account = provider.get_account()

    assert account.handle == "charlidamelio"
    assert account.follower_count > 1_000_000
    assert len(account.videos) >= 1
    assert account.videos[0].performance.views > 0
