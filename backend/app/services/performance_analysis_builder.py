"""Build performance_analysis from TikTok post data (WHAT happened — no LLM)."""

from __future__ import annotations

from ..models.analytics import EngagementMetrics, PerformanceMetrics
from ..models.content_analysis import PerformanceAnalysisSection
from ..models.content_types import ContentType
from ..providers import TikTokVideoData
from .content_intelligence.performance import build_performance_signals
from .content_metrics import apply_metrics_to_performance, metrics_from_row


def build_performance_analysis(
    post_data: TikTokVideoData,
    *,
    metrics_row: object | None = None,
) -> PerformanceAnalysisSection:
    """Inject measurable performance facts before merge."""

    perf_dict = post_data.performance.model_dump()
    user_metrics = metrics_from_row(metrics_row)
    merged_perf = apply_metrics_to_performance(perf_dict, user_metrics)
    performance = PerformanceMetrics(**merged_perf)

    views = max(performance.views, 1)
    engagement = EngagementMetrics(
        engagement_rate=round(
            (performance.likes + performance.comments + performance.shares + performance.saves)
            / views,
            4,
        ),
        share_rate=round(performance.shares / views, 4),
        save_rate=round(performance.saves / views, 4),
        like_to_view_ratio=round(performance.likes / views, 4),
        comment_to_view_ratio=round(performance.comments / views, 4),
        follower_conversion_rate=round(performance.followers_gained / views, 4),
    )

    content_type = getattr(post_data.video, "content_type", ContentType.VIDEO)
    if content_type == ContentType.IMAGE:
        summary = (
            f"The image post reached {performance.views:,} views with "
            f"{engagement.engagement_rate:.1%} engagement rate "
            f"({performance.likes:,} likes, {performance.comments:,} comments, "
            f"{performance.shares:,} shares, {performance.saves:,} saves)."
        )
    elif content_type == ContentType.CAROUSEL:
        summary = (
            f"The carousel post reached {performance.views:,} views with "
            f"{engagement.engagement_rate:.1%} engagement rate "
            f"({performance.likes:,} likes, {performance.comments:,} comments, "
            f"{performance.shares:,} shares, {performance.saves:,} saves)."
        )
    else:
        completion_pct = f"{performance.completion_rate * 100:.1f}%"
        summary = (
            f"The video reached {performance.views:,} views with "
            f"{engagement.engagement_rate:.1%} engagement rate "
            f"({performance.likes:,} likes, {performance.comments:,} comments, "
            f"{performance.shares:,} shares, {performance.saves:,} saves). "
            f"Completion rate was {completion_pct}."
        )
        if performance.average_watch_duration > 0:
            summary += (
                f" Average watch duration was {performance.average_watch_duration:.1f}s "
                f"on a {post_data.video.duration}s video."
            )

    post = post_data.video.model_copy()
    if metrics_row is not None:
        if getattr(metrics_row, "publish_date", None):
            post.publish_date = metrics_row.publish_date
        if getattr(metrics_row, "publish_time", None):
            post.publish_time = metrics_row.publish_time

    return PerformanceAnalysisSection(
        post=post,
        metrics=performance,
        engagement=engagement,
        performance_summary=summary,
        signals=build_performance_signals(
            performance,
            duration_seconds=post_data.video.duration,
        ),
    )
