"""TikTok provider wrapper that overlays user-saved Studio metrics."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy

from ..models.analytics import PerformanceMetrics
from ..services.video_metrics import apply_metrics_to_performance, metrics_from_row
from . import TikTokAccountData, TikTokProvider, TikTokVideoData


class UserMetricsTikTokProvider(TikTokProvider):
    """Wraps a TikTok provider and merges persisted VideoMetricsORM values."""

    def __init__(
        self,
        inner: TikTokProvider,
        metrics_getter: Callable[[str], object | None],
    ) -> None:
        self._inner = inner
        self._metrics_getter = metrics_getter

    def get_account(self) -> TikTokAccountData:
        account = self._inner.get_account()
        account.videos = [self._merge_video(v) for v in account.videos]
        return account

    def get_video(self, video_id: str) -> TikTokVideoData | None:
        video = self._inner.get_video(video_id)
        if video is None:
            return None
        return self._merge_video(video)

    def _merge_video(self, video: TikTokVideoData) -> TikTokVideoData:
        row = self._metrics_getter(video.video.video_id)
        if row is None:
            return video
        data = metrics_from_row(row)
        if not any(value is not None for value in data.values()):
            return video
        merged = deepcopy(video)
        perf_dict = merged.performance.model_dump()
        merged.performance = PerformanceMetrics(
            **apply_metrics_to_performance(perf_dict, data)
        )
        return merged
