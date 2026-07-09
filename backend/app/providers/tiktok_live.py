"""Live TikTok data provider — fetches real public profile and video metrics.

Uses TikTok's public web data via the tikwm.com mirror API. No API key required.
Set TIKTOK_PROVIDER=mock in tests or when offline.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass
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

_REQUEST_LOCK = threading.Lock()
_LAST_REQUEST_AT = 0.0
_ACCOUNT_CACHE: dict[str, tuple[float, TikTokAccountData]] = {}
_VIDEO_URL_CACHE: dict[str, tuple[float, str]] = {}
_VIDEO_BYTES_CACHE: dict[str, tuple[float, bytes, str]] = {}

_RATE_LIMIT_PATTERN = re.compile(r"limit|request/second|too many", re.IGNORECASE)


@dataclass(frozen=True)
class AccountFetchResult:
    """Result of a TikTok account fetch, optionally served from cache."""

    account: TikTokAccountData
    live_data_error: str | None = None


def clear_account_cache(handle: str | None = None) -> None:
    """Clear cached account data (all handles, or one handle). Used in tests."""

    if handle is None:
        _ACCOUNT_CACHE.clear()
        _VIDEO_URL_CACHE.clear()
        _VIDEO_BYTES_CACHE.clear()
        return
    normalized = normalize_tiktok_handle(handle)
    _ACCOUNT_CACHE.pop(normalized, None)
    keys_to_drop = [key for key in _VIDEO_URL_CACHE if key.endswith(f":{normalized}")]
    for key in keys_to_drop:
        _VIDEO_URL_CACHE.pop(key, None)
        _VIDEO_BYTES_CACHE.pop(key, None)


def _is_rate_limit_error(message: str) -> bool:
    return bool(_RATE_LIMIT_PATTERN.search(message))


def _is_retryable_status(status_code: int) -> bool:
    """Transient tikwm / gateway errors worth retrying."""

    return status_code in {429, 502, 503, 520, 521, 522, 523, 524, 531}


def _get_cached_account(handle: str, *, allow_stale: bool = False) -> TikTokAccountData | None:
    entry = _ACCOUNT_CACHE.get(handle)
    if entry is None:
        return None
    fetched_at, account = entry
    ttl = get_settings().tiktok_cache_ttl_seconds
    if allow_stale or (time.monotonic() - fetched_at) < ttl:
        return account
    return None


def _set_cached_account(handle: str, account: TikTokAccountData) -> None:
    _ACCOUNT_CACHE[handle] = (time.monotonic(), account)


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=get_settings().tiktok_fetch_timeout_seconds,
        headers={"User-Agent": "Lakarra-Content-Analyst/1.0"},
        follow_redirects=True,
    )


def _get_json(client: httpx.Client, path: str, *, params: dict) -> dict:
    settings = get_settings()
    last_error: TikTokFetchError | None = None

    for attempt in range(settings.tiktok_rate_limit_retries):
        with _REQUEST_LOCK:
            global _LAST_REQUEST_AT  # noqa: PLW0603
            elapsed = time.monotonic() - _LAST_REQUEST_AT
            if elapsed < 1.1:
                time.sleep(1.1 - elapsed)

            base = settings.tiktok_api_base_url.rstrip("/")
            try:
                response = client.get(f"{base}{path}", params=params)
            except httpx.HTTPError as exc:
                last_error = TikTokFetchError(f"TikTok data request failed: {exc}")
                _LAST_REQUEST_AT = time.monotonic()
            else:
                if response.status_code != 200:
                    message = f"TikTok data request failed (HTTP {response.status_code})."
                    last_error = TikTokFetchError(message)
                    _LAST_REQUEST_AT = time.monotonic()
                    if not _is_retryable_status(response.status_code):
                        raise last_error
                else:
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        raise TikTokFetchError(
                            "TikTok data provider returned invalid JSON."
                        ) from exc
                    if payload.get("code") != 0:
                        message = payload.get("msg") or "TikTok data request failed."
                        last_error = TikTokFetchError(message)
                        _LAST_REQUEST_AT = time.monotonic()
                        if not _is_rate_limit_error(message):
                            raise last_error
                    else:
                        _LAST_REQUEST_AT = time.monotonic()
                        return payload["data"]

        if attempt < settings.tiktok_rate_limit_retries - 1 and last_error is not None:
            logger.info(
                "tiktok_live.rate_limit_retry attempt=%s path=%s",
                attempt + 1,
                path,
            )
            time.sleep(settings.tiktok_rate_limit_retry_seconds)
            continue
        if last_error is not None:
            raise last_error

    raise TikTokFetchError("TikTok data request failed.")


def _post_json(client: httpx.Client, path: str, *, data: dict) -> dict:
    settings = get_settings()
    last_error: TikTokFetchError | None = None

    for attempt in range(settings.tiktok_rate_limit_retries):
        with _REQUEST_LOCK:
            global _LAST_REQUEST_AT  # noqa: PLW0603
            elapsed = time.monotonic() - _LAST_REQUEST_AT
            if elapsed < 1.1:
                time.sleep(1.1 - elapsed)

            base = settings.tiktok_api_base_url.rstrip("/")
            try:
                response = client.post(f"{base}{path}", data=data)
            except httpx.HTTPError as exc:
                last_error = TikTokFetchError(f"TikTok data request failed: {exc}")
                _LAST_REQUEST_AT = time.monotonic()
            else:
                if response.status_code != 200:
                    message = f"TikTok data request failed (HTTP {response.status_code})."
                    last_error = TikTokFetchError(message)
                    _LAST_REQUEST_AT = time.monotonic()
                    if not _is_retryable_status(response.status_code):
                        raise last_error
                else:
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        raise TikTokFetchError(
                            "TikTok data provider returned invalid JSON."
                        ) from exc
                    if payload.get("code") != 0:
                        message = payload.get("msg") or "TikTok data request failed."
                        last_error = TikTokFetchError(message)
                        _LAST_REQUEST_AT = time.monotonic()
                        if not _is_rate_limit_error(message):
                            raise last_error
                    else:
                        _LAST_REQUEST_AT = time.monotonic()
                        return payload["data"]

        if attempt < settings.tiktok_rate_limit_retries - 1 and last_error is not None:
            time.sleep(settings.tiktok_rate_limit_retry_seconds)
            continue
        if last_error is not None:
            raise last_error

    raise TikTokFetchError("TikTok data request failed.")


def _download_url_from_raw(raw: dict) -> str:
    for key in ("wmplay", "play", "hdplay"):
        url = raw.get(key)
        if url:
            return str(url)
    return ""


def _cache_key(handle: str, video_id: str) -> str:
    return f"{video_id}:{normalize_tiktok_handle(handle)}"


def _resolve_download_url(handle: str, video_id: str, raw: dict | None = None) -> str:
    key = _cache_key(handle, video_id)
    cached = _VIDEO_URL_CACHE.get(key)
    ttl = get_settings().tiktok_cache_ttl_seconds
    if cached and (time.monotonic() - cached[0]) < ttl:
        return cached[1]
    if raw is not None:
        url = _download_url_from_raw(raw)
        if url:
            _VIDEO_URL_CACHE[key] = (time.monotonic(), url)
            return url

    page_url = f"https://www.tiktok.com/@{handle}/video/{video_id}"
    with _client() as client:
        data = _post_json(client, "/api/", data={"url": page_url, "hd": 1})
    url = _download_url_from_raw(data)
    if url:
        _VIDEO_URL_CACHE[key] = (time.monotonic(), url)
    return url


def download_tiktok_video(handle: str, video_id: str) -> tuple[bytes, str, str] | None:
    """Download TikTok video bytes via tikwm CDN URL."""

    normalized = normalize_tiktok_handle(handle)
    if not normalized or not video_id:
        return None

    key = _cache_key(normalized, video_id)
    cached_bytes = _VIDEO_BYTES_CACHE.get(key)
    ttl = get_settings().tiktok_cache_ttl_seconds
    if cached_bytes and (time.monotonic() - cached_bytes[0]) < ttl:
        url_entry = _VIDEO_URL_CACHE.get(key)
        download_url = url_entry[1] if url_entry else ""
        return cached_bytes[1], cached_bytes[2], download_url

    download_url = _resolve_download_url(normalized, video_id)
    if not download_url:
        return None

    max_bytes = get_settings().max_upload_bytes
    timeout = get_settings().tiktok_fetch_timeout_seconds
    with _client() as client:
        with client.stream("GET", download_url, timeout=timeout) as response:
            if response.status_code != 200:
                raise TikTokFetchError(
                    f"TikTok video download failed (HTTP {response.status_code})."
                )
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise TikTokFetchError(
                        f"TikTok video exceeds max size ({max_bytes} bytes)."
                    )
                chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        return None

    mime_type = "video/mp4"
    _VIDEO_BYTES_CACHE[key] = (time.monotonic(), data, mime_type)
    return data, mime_type, download_url


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
    return TikTokVideoData(
        video=video,
        performance=performance,
        comments=[],
        download_url=_download_url_from_raw(raw),
    )


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

    def _fetch_account_fresh(self) -> tuple[TikTokAccountData, str | None]:
        posts_error: str | None = None
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
            try:
                raw_videos = self._fetch_videos(client)
            except TikTokFetchError as exc:
                logger.warning(
                    "tiktok_live.posts_fetch_failed handle=%s error=%s",
                    self._handle,
                    exc.message,
                )
                posts_error = exc.message
                raw_videos = []

        videos = [_video_from_raw(self._handle, raw) for raw in raw_videos]
        account = TikTokAccountData(
            handle=self._handle,
            follower_count=int(stats.get("followerCount") or 0),
            videos=videos,
        )
        return account, posts_error

    def fetch_account(self) -> AccountFetchResult:
        """Fetch account data, using cache and stale fallback when live fetch fails."""

        cached = _get_cached_account(self._handle)
        if cached is not None:
            return AccountFetchResult(account=cached)

        live_data_error: str | None = None
        try:
            account, posts_error = self._fetch_account_fresh()
        except TikTokFetchError as exc:
            stale = _get_cached_account(self._handle, allow_stale=True)
            if stale is not None:
                logger.warning(
                    "tiktok_live.using_stale_cache handle=%s error=%s",
                    self._handle,
                    exc.message,
                )
                return AccountFetchResult(
                    account=stale,
                    live_data_error=(
                        f"Could not refresh live TikTok data: {exc.message}. "
                        "Showing cached data."
                    ),
                )
            raise

        if posts_error and not account.videos:
            stale = _get_cached_account(self._handle, allow_stale=True)
            if stale is not None and stale.videos:
                account = TikTokAccountData(
                    handle=account.handle,
                    follower_count=account.follower_count,
                    videos=stale.videos,
                )
                live_data_error = (
                    f"Could not refresh video list: {posts_error}. Showing cached videos."
                )
            else:
                live_data_error = f"Could not load video list: {posts_error}."
        elif posts_error:
            live_data_error = f"Some live data may be stale: {posts_error}"

        if account.videos:
            _set_cached_account(self._handle, account)

        return AccountFetchResult(account=account, live_data_error=live_data_error)

    def get_account(self) -> TikTokAccountData:
        return self.fetch_account().account

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
