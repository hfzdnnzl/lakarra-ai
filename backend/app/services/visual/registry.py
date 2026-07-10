"""Registry of content-type visual strategies."""

from __future__ import annotations

from ...models.content_types import ContentType
from .strategies.base import ContentTypeVisualStrategy
from .strategies.carousel import CarouselVisualStrategy
from .strategies.image import ImageVisualStrategy
from .strategies.video import VideoVisualStrategy

_STRATEGIES: dict[ContentType, ContentTypeVisualStrategy] = {
    ContentType.VIDEO: VideoVisualStrategy(),
    ContentType.IMAGE: ImageVisualStrategy(),
    ContentType.CAROUSEL: CarouselVisualStrategy(),
}


def register_visual_strategy(
    content_type: ContentType,
    strategy: ContentTypeVisualStrategy,
) -> None:
    """Register or replace a content-type visual strategy (extension point)."""

    _STRATEGIES[content_type] = strategy


def get_visual_strategy(content_type: ContentType) -> ContentTypeVisualStrategy:
    try:
        return _STRATEGIES[content_type]
    except KeyError as exc:
        raise ValueError(f"No visual strategy registered for: {content_type}") from exc
