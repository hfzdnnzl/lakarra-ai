"""Data provider interfaces for the Content Analyst agent.

Supports multiple data sources via pluggable providers. The default ``live``
provider fetches real public TikTok metrics; ``mock`` is for offline tests only.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from random import Random

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.analytics import (
    CompetitorAccountData,
    PerformanceMetrics,
    VideoInfo,
    normalize_tiktok_handle,
)
from ..models.db import Content
from ..repositories.content_repository import ContentRepository


@dataclass
class TikTokVideoData:
    """Raw video data from a TikTok provider."""

    video: VideoInfo
    performance: PerformanceMetrics
    comments: list[str] = field(default_factory=list)


@dataclass
class TikTokAccountData:
    """Raw account-level data from a TikTok provider."""

    handle: str = "lakarra"
    follower_count: int = 0
    videos: list[TikTokVideoData] = field(default_factory=list)


class TikTokProvider(ABC):
    """Interface for Lakarra TikTok account and video data."""

    @abstractmethod
    def get_account(self) -> TikTokAccountData:
        """Fetch Lakarra account data and published videos."""

    @abstractmethod
    def get_video(self, video_id: str) -> TikTokVideoData | None:
        """Fetch a single published video by ID."""


class CompetitorProvider(ABC):
    """Interface for competitor TikTok account data."""

    @abstractmethod
    def get_account(self, handle: str) -> CompetitorAccountData:
        """Fetch competitor account profile and metrics."""

    @abstractmethod
    def list_known_competitors(self) -> list[str]:
        """Return handles of tracked competitor accounts."""


class InternalContentProvider(ABC):
    """Interface for Lakarra CMS content (Content Creator output)."""

    @abstractmethod
    def get_content(self, content_id: str) -> Content | None:
        """Fetch a content item by ID."""

    @abstractmethod
    def list_posted_content(self, *, limit: int = 50) -> list[Content]:
        """List published/analyzed content for historical analysis."""

    @abstractmethod
    def list_review_queue(self) -> list[Content]:
        """List content awaiting analyst review."""


# ---------------------------------------------------------------------------
# Mock implementations
# ---------------------------------------------------------------------------

_MOCK_VIDEOS = [
    {
        "video_id": "lk-001",
        "title": "Wedding invite reveal",
        "category": "aesthetic",
        "hook": "POV: your guests open the most beautiful invite",
        "duration": 22,
        "views": 45200,
        "likes": 3200,
        "comments": 187,
        "shares": 412,
        "saves": 890,
    },
    {
        "video_id": "lk-002",
        "title": "Digital vs paper invites",
        "category": "educational",
        "hook": "Stop wasting money on paper invites",
        "duration": 35,
        "views": 128000,
        "likes": 8900,
        "comments": 542,
        "shares": 1200,
        "saves": 2100,
    },
    {
        "video_id": "lk-003",
        "title": "Behind the scenes design",
        "category": "behind_the_scenes",
        "hook": "How we design a wedding invite in 60 seconds",
        "duration": 58,
        "views": 23100,
        "likes": 1100,
        "comments": 67,
        "shares": 89,
        "saves": 340,
    },
    {
        "video_id": "lk-004",
        "title": "Customer testimonial",
        "category": "testimonial",
        "hook": "She cried when she saw her invite",
        "duration": 28,
        "views": 67500,
        "likes": 5400,
        "comments": 312,
        "shares": 678,
        "saves": 1450,
    },
    {
        "video_id": "lk-005",
        "title": "Trend adaptation",
        "category": "trend_adaptation",
        "hook": "Using this trend for wedding invites",
        "duration": 15,
        "views": 189000,
        "likes": 14200,
        "comments": 890,
        "shares": 2300,
        "saves": 3800,
    },
]

_MOCK_COMPETITORS = {
    "paperlesspost": CompetitorAccountData(
        handle="paperlesspost",
        follower_count=245000,
        posting_frequency="4-5 posts/week",
        average_views=85000,
        engagement_rate=0.045,
        content_categories=["educational", "aesthetic", "testimonial"],
        posting_schedule=["Tue 18:00", "Thu 19:00", "Sat 11:00"],
        recurring_hooks=["Did you know...", "Wedding tip:", "Save this for later"],
        recurring_themes=["sustainability", "cost savings", "design inspiration"],
        video_styles=["talking head", "screen recording", "before/after"],
        editing_patterns=["fast cuts", "text overlays", "trending audio"],
        cta_style="Link in bio for free templates",
    ),
    "greenvelope": CompetitorAccountData(
        handle="greenvelope",
        follower_count=89000,
        posting_frequency="3 posts/week",
        average_views=42000,
        engagement_rate=0.038,
        content_categories=["educational", "pov", "product_comparison"],
        posting_schedule=["Mon 17:00", "Wed 20:00", "Fri 12:00"],
        recurring_hooks=["POV:", "Wedding planners hate this", "The truth about..."],
        recurring_themes=["eco-friendly", "budget weddings", "DIY"],
        video_styles=["POV", "split screen", "slideshow"],
        editing_patterns=["slow reveal", "caption-heavy", "soft transitions"],
        cta_style="Try free at greenvelope.com",
    ),
}


def _build_performance(raw: dict, rng: Random) -> PerformanceMetrics:
    views = raw["views"]
    likes = raw["likes"]
    comments = raw["comments"]
    shares = raw["shares"]
    saves = raw["saves"]
    completion = round(rng.uniform(0.35, 0.72), 2)
    avg_watch = round(raw["duration"] * completion * rng.uniform(0.85, 1.0), 1)
    curve = [round(max(0.1, 1.0 - i * rng.uniform(0.08, 0.15)), 2) for i in range(10)]
    return PerformanceMetrics(
        views=views,
        reach=int(views * rng.uniform(0.7, 0.95)),
        watch_time=round(views * avg_watch / 60, 1),
        average_watch_duration=avg_watch,
        completion_rate=completion,
        retention_curve=curve,
        likes=likes,
        comments=comments,
        shares=shares,
        saves=saves,
        profile_visits=int(views * rng.uniform(0.02, 0.06)),
        followers_gained=int(views * rng.uniform(0.001, 0.005)),
        link_clicks=int(views * rng.uniform(0.01, 0.03)) if rng.random() > 0.3 else None,
    )


def _mock_comments(rng: Random) -> list[str]:
    pool = [
        "How much does this cost?",
        "This is so beautiful!",
        "Can I customize the colors?",
        "Link?",
        "We used Lakarra for our wedding and loved it",
        "Is this available for Indian weddings?",
        "The animation is gorgeous",
        "Need this for my sister's wedding",
        "Better than paper invites honestly",
        "What's the website?",
    ]
    return rng.sample(pool, k=rng.randint(5, 8))


class MockTikTokProvider(TikTokProvider):
    """Deterministic mock TikTok data for development and testing."""

    def __init__(self, handle: str, *, seed: int = 42) -> None:
        self._handle = normalize_tiktok_handle(handle)
        self._rng = Random(seed)

    def get_account(self) -> TikTokAccountData:
        videos = []
        base_date = datetime.now(UTC) - timedelta(days=60)
        for i, raw in enumerate(_MOCK_VIDEOS):
            pub = base_date + timedelta(days=i * 12, hours=self._rng.randint(10, 21))
            video = VideoInfo(
                video_id=raw["video_id"],
                url=f"https://tiktok.com/@{self._handle}/video/{raw['video_id']}",
                title=raw["title"],
                caption=f"{raw['hook']} #wedding #digitalinvite #{self._handle}",
                hashtags=["wedding", "digitalinvite", self._handle, raw["category"]],
                publish_date=pub.strftime("%Y-%m-%d"),
                publish_time=pub.strftime("%H:%M"),
                duration=raw["duration"],
                thumbnail=f"/mock/thumbnails/{raw['video_id']}.jpg",
                content_category=raw["category"],
            )
            perf = _build_performance(raw, self._rng)
            videos.append(
                TikTokVideoData(
                    video=video, performance=perf, comments=_mock_comments(self._rng)
                )
            )
        return TikTokAccountData(
            handle=self._handle, follower_count=34200, videos=videos
        )

    def get_video(self, video_id: str) -> TikTokVideoData | None:
        for v in self.get_account().videos:
            if v.video.video_id == video_id:
                return v
        return None


class MockCompetitorProvider(CompetitorProvider):
    """Mock competitor data for development and testing."""

    def get_account(self, handle: str) -> CompetitorAccountData:
        key = handle.lstrip("@").lower()
        if key in _MOCK_COMPETITORS:
            return _MOCK_COMPETITORS[key]
        return CompetitorAccountData(
            handle=key,
            follower_count=15000,
            posting_frequency="2 posts/week",
            average_views=8000,
            engagement_rate=0.025,
            content_categories=["educational"],
            posting_schedule=["Wed 18:00"],
            recurring_hooks=["Check this out"],
            recurring_themes=["weddings"],
            video_styles=["slideshow"],
            editing_patterns=["basic cuts"],
            cta_style="Visit our website",
        )

    def list_known_competitors(self) -> list[str]:
        return list(_MOCK_COMPETITORS.keys())


class InternalContentProviderImpl(InternalContentProvider):
    """Reads Lakarra CMS content via the content repository."""

    def __init__(self, session: Session) -> None:
        self._repo = ContentRepository(session)

    def get_content(self, content_id: str) -> Content | None:
        return self._repo.get(content_id)

    def list_posted_content(self, *, limit: int = 50) -> list[Content]:
        items, _ = self._repo.list(status="posted", page=1, page_size=limit)
        analyzed, _ = self._repo.list(status="analyzed", page=1, page_size=limit)
        promoted, _ = self._repo.list(status="promoted", page=1, page_size=limit)
        seen: set[str] = set()
        result: list[Content] = []
        for item in items + analyzed + promoted:
            if item.id not in seen:
                seen.add(item.id)
                result.append(item)
        return result[:limit]

    def list_review_queue(self) -> list[Content]:
        review, _ = self._repo.list(status="review", page=1, page_size=100)
        approved, _ = self._repo.list(status="approved", page=1, page_size=100)
        return review + approved


def build_tiktok_provider(handle: str) -> TikTokProvider:
    """Build a TikTok data provider for the given @handle."""

    normalized = normalize_tiktok_handle(handle)
    if get_settings().tiktok_provider == "mock":
        return MockTikTokProvider(normalized)
    from .tiktok_live import LiveTikTokProvider

    return LiveTikTokProvider(normalized)


def build_competitor_provider() -> CompetitorProvider:
    if get_settings().tiktok_provider == "mock":
        return MockCompetitorProvider()
    from .tiktok_live import LiveCompetitorProvider

    return LiveCompetitorProvider()


def build_internal_content_provider(session: Session) -> InternalContentProvider:
    return InternalContentProviderImpl(session)
