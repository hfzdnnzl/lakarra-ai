"""Content metrics validation and merge helpers (VIDEO, IMAGE, and CAROUSEL)."""

from __future__ import annotations

from typing import Any

from ..models.content_types import ContentType

REQUIRED_METRIC_FIELDS: tuple[str, ...] = (
    "views",
    "likes",
    "comments",
    "shares",
    "saves",
)

OPTIONAL_METRIC_FIELDS: tuple[str, ...] = (
    "reach",
    "watch_time",
    "average_watch_duration",
    "completion_rate",
    "followers_gained",
    "photos_viewed",
)

VIDEO_OPTIONAL_METRIC_FIELDS: tuple[str, ...] = (
    "reach",
    "watch_time",
    "average_watch_duration",
    "completion_rate",
    "followers_gained",
)

IMAGE_OPTIONAL_METRIC_FIELDS: tuple[str, ...] = (
    "reach",
    "watch_time",
    "followers_gained",
    "photos_viewed",
)

CAROUSEL_OPTIONAL_METRIC_FIELDS: tuple[str, ...] = IMAGE_OPTIONAL_METRIC_FIELDS

METRIC_FIELD_LABELS: dict[str, str] = {
    "views": "Views",
    "likes": "Likes",
    "comments": "Comments",
    "shares": "Shares",
    "saves": "Saves",
    "reach": "Total viewers",
    "watch_time": "Total play time (hh:mm:ss)",
    "average_watch_duration": "Average watch time (seconds)",
    "completion_rate": "Watched full video (%)",
    "followers_gained": "New followers",
    "photos_viewed": "Photos viewed",
}


def optional_fields_for(content_type: ContentType) -> tuple[str, ...]:
    if content_type == ContentType.VIDEO:
        return VIDEO_OPTIONAL_METRIC_FIELDS
    if content_type == ContentType.IMAGE:
        return IMAGE_OPTIONAL_METRIC_FIELDS
    return CAROUSEL_OPTIONAL_METRIC_FIELDS


def metrics_from_row(row: Any | None) -> dict[str, float | int | None]:
    if row is None:
        return {field: None for field in REQUIRED_METRIC_FIELDS + OPTIONAL_METRIC_FIELDS}
    return {
        "views": row.views,
        "likes": row.likes,
        "comments": row.comments,
        "shares": row.shares,
        "saves": row.saves,
        "reach": row.reach,
        "watch_time": row.watch_time,
        "average_watch_duration": row.average_watch_duration,
        "completion_rate": row.completion_rate,
        "photos_viewed": row.photos_viewed,
        "profile_visits": row.profile_visits,
        "followers_gained": row.followers_gained,
        "link_clicks": row.link_clicks,
    }


def missing_required(metrics: dict[str, float | int | None]) -> list[str]:
    missing: list[str] = []
    for field in REQUIRED_METRIC_FIELDS:
        value = metrics.get(field)
        if value is None:
            missing.append(field)
    return missing


def metrics_complete(
    metrics: dict[str, float | int | None],
    *,
    content_type: ContentType = ContentType.VIDEO,
) -> bool:
    return len(missing_required(metrics)) == 0


def apply_metrics_to_performance(
    performance: dict[str, Any], metrics: dict[str, float | int | None]
) -> dict[str, Any]:
    merged = dict(performance)
    for field in REQUIRED_METRIC_FIELDS + OPTIONAL_METRIC_FIELDS:
        value = metrics.get(field)
        if value is not None:
            merged[field] = value
    views = int(merged.get("views") or 0)
    likes = int(merged.get("likes") or 0)
    comments = int(merged.get("comments") or 0)
    shares = int(merged.get("shares") or 0)
    saves = int(merged.get("saves") or 0)
    if views > 0:
        merged["engagement_rate"] = round((likes + comments + shares + saves) / views, 4)
        merged["share_rate"] = round(shares / views, 4)
        merged["save_rate"] = round(saves / views, 4)
        merged["like_to_view_ratio"] = round(likes / views, 4)
        merged["comment_to_view_ratio"] = round(comments / views, 4)
    return merged


def content_display_label(*, title: str = "", caption: str = "") -> str:
    cap = caption.strip()
    if cap:
        first_line = cap.split("\n")[0].strip()
        return first_line[:120] if first_line else cap[:120]
    cleaned = title.strip()
    if cleaned and not cleaned.lower().startswith("video "):
        return cleaned[:120]
    return cleaned or "Untitled post"


video_display_label = content_display_label


def resolve_publish_metadata(
    row: Any | None,
    *,
    default_date: str = "",
    default_time: str = "",
) -> tuple[str, str]:
    date = (row.publish_date if row and row.publish_date else None) or default_date
    time = (row.publish_time if row and row.publish_time else None) or default_time
    return date, time


def infer_content_type_from_mime(mime_type: str | None) -> ContentType | None:
    if not mime_type:
        return None
    if mime_type == "application/vnd.lakarra.carousel+json":
        return ContentType.CAROUSEL
    if mime_type.startswith("image/"):
        return ContentType.IMAGE
    if mime_type.startswith("video/"):
        return ContentType.VIDEO
    return None
