"""Tests for live TikTok data fetching."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.config import get_settings
from app.errors import TikTokFetchError
from app.models.analytics import PerformanceMetrics, VideoInfo
from app.providers import TikTokAccountData, TikTokVideoData
from app.providers.tiktok_live import LiveTikTokProvider, clear_account_cache


@pytest.fixture(autouse=True)
def _clear_tiktok_cache():
    clear_account_cache()
    yield
    clear_account_cache()


def _sample_account() -> TikTokAccountData:
    video = TikTokVideoData(
        video=VideoInfo(
            video_id="v1",
            url="https://www.tiktok.com/@brand/video/v1",
            title="Test video",
            caption="Test",
            hashtags=[],
            publish_date="2026-01-01",
            publish_time="12:00",
            duration=30,
            thumbnail="",
            content_category="general",
        ),
        performance=PerformanceMetrics(
            views=1000,
            reach=1000,
            watch_time=500.0,
            average_watch_duration=30.0,
            completion_rate=0.0,
            retention_curve=[],
            likes=100,
            comments=10,
            shares=5,
            saves=20,
            profile_visits=0,
            followers_gained=0,
            link_clicks=None,
        ),
        comments=[],
    )
    return TikTokAccountData(handle="brand", follower_count=5000, videos=[video])


class TestTikTokRateLimitAndCache:
    def test_get_json_retries_on_rate_limit_message(self, monkeypatch):
        monkeypatch.setenv("TIKTOK_RATE_LIMIT_RETRIES", "3")
        monkeypatch.setenv("TIKTOK_RATE_LIMIT_RETRY_SECONDS", "0")
        get_settings.cache_clear()

        from app.providers import tiktok_live

        rate_limit_payload = {"code": -1, "msg": "Free Api Limit: 1 request/second."}
        responses = [
            MagicMock(status_code=200, json=lambda: rate_limit_payload),
            MagicMock(status_code=200, json=lambda: {"code": 0, "data": {"ok": True}}),
        ]

        mock_client = MagicMock()
        mock_client.get.side_effect = responses

        data = tiktok_live._get_json(mock_client, "/api/user/info", params={"unique_id": "brand"})
        assert data == {"ok": True}
        assert mock_client.get.call_count == 2

    def test_fetch_account_uses_cache_within_ttl(self, monkeypatch):
        monkeypatch.setenv("TIKTOK_CACHE_TTL_SECONDS", "300")
        get_settings.cache_clear()

        provider = LiveTikTokProvider("brand")
        sample = _sample_account()

        with patch.object(
            provider, "_fetch_account_fresh", return_value=(sample, None)
        ) as fetch:
            first = provider.fetch_account()
            second = provider.fetch_account()

        assert first.account.handle == "brand"
        assert second.account.handle == "brand"
        assert fetch.call_count == 1

    def test_fetch_account_survives_posts_failure(self, monkeypatch):
        get_settings.cache_clear()
        provider = LiveTikTokProvider("brand")

        def fake_fresh():
            return (
                TikTokAccountData(handle="brand", follower_count=999, videos=[]),
                "TikTok data request failed (HTTP 531).",
            )

        with patch.object(provider, "_fetch_account_fresh", side_effect=fake_fresh):
            result = provider.fetch_account()

        assert result.account.follower_count == 999
        assert result.live_data_error is not None
        assert "531" in result.live_data_error

    def test_fetch_account_returns_stale_cache_on_failure(self, monkeypatch):
        monkeypatch.setenv("TIKTOK_CACHE_TTL_SECONDS", "0")
        get_settings.cache_clear()

        provider = LiveTikTokProvider("brand")
        sample = _sample_account()

        with patch.object(provider, "_fetch_account_fresh", return_value=(sample, None)):
            provider.fetch_account()

        with patch.object(
            provider,
            "_fetch_account_fresh",
            side_effect=TikTokFetchError("Free Api Limit: 1 request/second."),
        ):
            result = provider.fetch_account()

        assert result.account.handle == "brand"
        assert result.live_data_error is not None
        assert "cached data" in result.live_data_error.lower()

    def test_fetch_account_raises_when_no_cache_and_fetch_fails(self):
        provider = LiveTikTokProvider("brand")
        with patch.object(
            provider,
            "_fetch_account_fresh",
            side_effect=TikTokFetchError("Free Api Limit: 1 request/second."),
        ):
            with pytest.raises(TikTokFetchError):
                provider.fetch_account()


class TestTikTokDownload:
    def test_download_url_from_raw_prefers_wmplay(self):
        from app.providers.tiktok_live import _download_url_from_raw

        url = _download_url_from_raw(
            {"wmplay": "https://cdn.example/wm.mp4", "play": "https://cdn.example/play.mp4"}
        )
        assert url == "https://cdn.example/wm.mp4"

    def test_download_tiktok_video_uses_cache(self, monkeypatch):
        from app.providers import tiktok_live

        monkeypatch.setenv("TIKTOK_CACHE_TTL_SECONDS", "300")
        get_settings.cache_clear()

        key = "v1:brand"
        tiktok_live._VIDEO_BYTES_CACHE[key] = (
            tiktok_live.time.monotonic(),
            b"cached-video",
            "video/mp4",
        )
        tiktok_live._VIDEO_URL_CACHE[key] = (tiktok_live.time.monotonic(), "https://cdn.example/v.mp4")

        result = tiktok_live.download_tiktok_video("brand", "v1")
        assert result == (b"cached-video", "video/mp4", "https://cdn.example/v.mp4")


@pytest.mark.integration
def test_live_tiktok_fetches_real_account(monkeypatch):
    monkeypatch.setenv("TIKTOK_PROVIDER", "live")
    get_settings.cache_clear()
    provider = LiveTikTokProvider("charlidamelio")
    try:
        account = provider.get_account()
    except TikTokFetchError:
        pytest.skip("tikwm unavailable or network blocked")

    assert account.handle == "charlidamelio"
    assert account.follower_count > 1_000_000
    assert len(account.videos) >= 1
    assert account.videos[0].performance.views > 0
