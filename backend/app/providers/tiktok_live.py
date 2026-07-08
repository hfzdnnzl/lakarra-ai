"""Live TikTok data provider — fetches real public profile and video metrics.

Uses TikTok's public web data via the tikwm.com mirror API. No API key required.
Set TIKTOK_PROVIDER=mock in tests or when offline.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

import httpx

from app.providers import CompetitorProvider, TikTokAccountData, TikTokProvider, TikTokVideoData

from ..config import get_settings
from ..errors import TikTokFetchError
from ..models.analytics import (
    CompetitorAccountData,
    PerformanceMetrics,
    VideoInfo,
    normalize_tiktok_handle,
)

logger = logging.getLogger("lakarra.tiktok_live")

_LAST_REQUEST_AT = 0.0


def _rate_limit() -> None:
    """tikwm free tier allows ~1 request/second."""

    global _LAST_REQUEST_AT  # noqa: PLW0603
    elapsed = time.monotonic() - _LAST_REQUEST_AT
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)
    _LAST_REQUEST_AT = time.monotonic()


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=get_settings().tiktok_fetch_timeout_seconds,
        headers={"User-Agent": "Lakarra-Content-Analyst/1.0"},
        follow_redirects=True,
    )


def _get_json(client: httpx.Client, path: str, *, params: dict) -> dict:
    _rate_limit()
    base = get_settings().tiktok_api_base_url.rstrip("/")
    response = client.get(f"{base}{path}", params=params)
    if response.status_code != 200:
        raise TikTokFetchError(
            f"TikTok data request failed (HTTP {response.status_code})."
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise TikTokFetchError("TikTok data provider returned invalid JSON.") from exc
    if payload.get("code") != 0:
        raise TikTokFetchError(payload.get("msg") or "TikTok data request failed.")
    return payload["data"]


def _caption_from_video(raw: dict) -> str:
    desc = raw.get("desc") or raw.get("title") or ""
    if desc:
        return str(desc)
    parts = raw.get("content_desc") or []
    if isinstance(parts, list):
        return " ".join(str(p) for p in parts if p)
    return ""


def _hashtags_from_caption(caption: str) -> list[str]:
    tags = []
    for token in caption.split():
        if token.startswith("#") and len(token) > 1:
            tags.append(token.lstrip("#"))
    return tags


def _video_from_raw(handle: str, raw: dict) -> TikTokVideoData:
    video_id = str(raw["video_id"])
    caption = _caption_from_video(raw)
    create_time = int(raw.get("create_time") or 0)
    published = datetime.fromtimestamp(create_time, tz=UTC) if create_time else None
    views = int(raw.get("play_count") or 0)
    likes = int(raw.get("digg_count") or 0)
    comments = int(raw.get("comment_count") or 0)
    shares = int(raw.get("share_count") or 0)
    saves = int(raw.get("collect_count") or 0)
    duration = int(raw.get("duration") or 0)

    video = VideoInfo(
        video_id=video_id,
        url=f"https://www.tiktok.com/@{handle}/video/{video_id}",
        title=caption[:120] if caption else f"Video {video_id}",
        caption=caption,
        hashtags=_hashtags_from_caption(caption),
        publish_date=published.strftime("%Y-%m-%d") if published else "",
        publish_time=published.strftime("%H:%M") if published else "",
        duration=duration,
        thumbnail=raw.get("cover") or raw.get("origin_cover") or "",
        content_category="general",
    )
    performance = PerformanceMetrics(
        views=views,
        reach=views,
        watch_time=round(views * max(duration, 1) / 60, 1),
        average_watch_duration=float(duration),
        completion_rate=0.0,
        retention_curve=[],
        likes=likes,
        comments=comments,
        shares=shares,
        saves=saves,
        profile_visits=0,
        followers_gained=0,
        link_clicks=None,
    )
    return TikTokVideoData(video=video, performance=performance, comments=[])


class LiveTikTokProvider(TikTokProvider):
    """Fetches real public TikTok account and video metrics."""

    def __init__(self, handle: str) -> None:
        self._handle = normalize_tiktok_handle(handle)
        if not self._handle:
            raise TikTokFetchError("TikTok handle is required.")

    def _fetch_videos(self, client: httpx.Client) -> list[dict]:
        max_videos = get_settings().tiktok_max_videos
        collected: list[dict] = []
        cursor = 0
        while len(collected) < max_videos:
            batch_size = min(35, max_videos - len(collected))
            data = _get_json(
                client,
                "/api/user/posts",
                params={
                    "unique_id": self._handle,
                    "count": batch_size,
                    "cursor": cursor,
                },
            )
            batch = data.get("videos") or []
            if not batch:
                break
            collected.extend(batch)
            if not data.get("hasMore"):
                break
            cursor = data.get("cursor") or 0
        return collected[:max_videos]

    def get_account(self) -> TikTokAccountData:
        with _client() as client:
            info = _get_json(
                client, "/api/user/info", params={"unique_id": self._handle}
            )
            user = info.get("user") or {}
            stats = info.get("stats") or {}
            if user.get("privateAccount"):
                raise TikTokFetchError(
                    f"@{self._handle} is a private account and cannot be analyzed."
                )
            raw_videos = self._fetch_videos(client)

        videos = [_video_from_raw(self._handle, raw) for raw in raw_videos]
        return TikTokAccountData(
            handle=self._handle,
            follower_count=int(stats.get("followerCount") or 0),
            videos=videos,
        )

    def get_video(self, video_id: str) -> TikTokVideoData | None:
        account = self.get_account()
        for video in account.videos:
            if video.video.video_id == video_id:
                return video
        return None


class LiveCompetitorProvider(CompetitorProvider):
    """Fetches real competitor account metadata from TikTok."""

    def get_account(self, handle: str) -> CompetitorAccountData:
        normalized = normalize_tiktok_handle(handle)
        provider = LiveTikTokProvider(normalized)
        account = provider.get_account()
        videos = account.videos
        avg_views = (
            sum(v.performance.views for v in videos) // len(videos) if videos else 0
        )
        engagements = [
            (v.performance.likes + v.performance.comments + v.performance.shares)
            / max(v.performance.views, 1)
            for v in videos
        ]
        engagement_rate = sum(engagements) / len(engagements) if engagements else 0.0

        hooks: list[str] = []
        for v in videos[:5]:
            caption = v.video.caption.strip()
            if caption:
                hooks.append(caption.split("\n")[0][:100])

        return CompetitorAccountData(
            handle=normalized,
            follower_count=account.follower_count,
            posting_frequency=_estimate_posting_frequency(videos),
            average_views=avg_views,
            engagement_rate=round(engagement_rate, 4),
            content_categories=["general"],
            posting_schedule=_posting_schedule(videos),
            recurring_hooks=hooks,
            recurring_themes=[],
            video_styles=[],
            editing_patterns=[],
            cta_style="",
        )

    def list_known_competitors(self) -> list[str]:
        return []


def _estimate_posting_frequency(videos: list[TikTokVideoData]) -> str:
    if len(videos) < 2:
        return "unknown"
    dates = sorted(
        v.video.publish_date for v in videos if v.video.publish_date
    )
    if len(dates) < 2:
        return "unknown"
    return f"~{len(dates)} posts in sample window"


def _posting_schedule(videos: list[TikTokVideoData]) -> list[str]:
    slots: list[str] = []
    for v in videos[:10]:
        if v.video.publish_date and v.video.publish_time:
            slots.append(f"{v.video.publish_date} {v.video.publish_time}")
    return slots
