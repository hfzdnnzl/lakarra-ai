"""Deterministic performance signals used by intelligence components."""

from __future__ import annotations

from app.models.analytics import PerformanceMetrics
from app.models.content_intelligence import (
    EvidenceKind,
    EvidenceRef,
    PerformanceSignal,
    PerformanceSignalSet,
)


def _ratio_signal(
    name: str,
    numerator: float,
    denominator: float,
    *,
    description: str,
) -> PerformanceSignal:
    if denominator <= 0:
        return PerformanceSignal(name=name, unit="ratio", available=False)
    value = round(numerator / denominator, 4)
    return PerformanceSignal(
        name=name,
        value=value,
        unit="ratio",
        evidence=EvidenceRef(
            id=f"performance.{name}",
            kind=EvidenceKind.METRIC,
            signal=name,
            description=description,
            observed_value=value,
        ),
    )


def build_performance_signals(
    metrics: PerformanceMetrics,
    *,
    duration_seconds: int = 0,
) -> PerformanceSignalSet:
    """Calculate measurable ratios without inferring unsupported outcomes."""

    views = float(metrics.views)
    total_engagement = metrics.likes + metrics.comments + metrics.shares + metrics.saves
    signals = [
        _ratio_signal(
            "engagement_rate",
            total_engagement,
            views,
            description="Total likes, comments, shares, and saves divided by views.",
        ),
        _ratio_signal(
            "share_rate",
            metrics.shares,
            views,
            description="Shares divided by views.",
        ),
        _ratio_signal(
            "save_rate",
            metrics.saves,
            views,
            description="Saves divided by views.",
        ),
        _ratio_signal(
            "follower_conversion_rate",
            metrics.followers_gained,
            views,
            description="Followers gained divided by views.",
        ),
    ]

    unavailable: list[str] = []
    if duration_seconds > 0 and metrics.average_watch_duration > 0:
        signals.append(
            _ratio_signal(
                "watch_duration_ratio",
                metrics.average_watch_duration,
                duration_seconds,
                description="Average watch duration divided by video duration.",
            )
        )
    else:
        unavailable.append("watch_duration_ratio")

    if metrics.completion_rate > 0:
        signals.append(
            PerformanceSignal(
                name="completion_rate",
                value=metrics.completion_rate,
                unit="ratio",
                evidence=EvidenceRef(
                    id="performance.completion_rate",
                    kind=EvidenceKind.METRIC,
                    signal="completion_rate",
                    description="Platform-reported completion rate.",
                    observed_value=metrics.completion_rate,
                ),
            )
        )
    else:
        unavailable.append("completion_rate")

    if metrics.link_clicks is not None:
        signals.append(
            _ratio_signal(
                "link_click_rate",
                metrics.link_clicks,
                views,
                description="Link clicks divided by views.",
            )
        )
    else:
        unavailable.append("link_click_rate")

    unavailable.extend(signal.name for signal in signals if not signal.available)
    return PerformanceSignalSet(signals=signals, unavailable_signals=sorted(set(unavailable)))
