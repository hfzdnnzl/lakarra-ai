"""Tests for user metrics overlay on TikTok provider data."""

from __future__ import annotations

from dataclasses import dataclass

from app.providers import MockTikTokProvider
from app.providers.metrics_overlay import UserMetricsTikTokProvider
from app.services.video_metrics import metrics_complete


@dataclass
class _FakeMetricsRow:
    views: int | None = 99_999
    likes: int | None = 5_000
    comments: int | None = 100
    shares: int | None = 50
    saves: int | None = 200
    reach: int | None = None
    watch_time: float | None = None
    average_watch_duration: float | None = None
    completion_rate: float | None = None
    profile_visits: int | None = None
    followers_gained: int | None = None
    link_clicks: int | None = None
    user_notes: str | None = "Promoted post"


def test_user_metrics_overlay_merges_saved_values():
    inner = MockTikTokProvider("lakarra")
    rows = {"lk-001": _FakeMetricsRow()}

    provider = UserMetricsTikTokProvider(inner, rows.get)
    video = provider.get_video("lk-001")
    assert video is not None
    assert video.performance.views == 99_999
    assert video.performance.likes == 5_000

    account = provider.get_account()
    first = next(v for v in account.videos if v.video.video_id == "lk-001")
    assert first.performance.views == 99_999

    from app.services.video_metrics import metrics_from_row

    assert metrics_complete(metrics_from_row(rows["lk-001"]))


def test_user_metrics_overlay_leaves_missing_rows_unchanged():
    inner = MockTikTokProvider("lakarra")
    provider = UserMetricsTikTokProvider(inner, lambda _vid: None)
    raw = inner.get_video("lk-001")
    merged = provider.get_video("lk-001")
    assert raw is not None and merged is not None
    assert merged.performance.views == raw.performance.views
