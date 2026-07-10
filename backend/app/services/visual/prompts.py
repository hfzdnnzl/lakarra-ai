"""Visual prompt resolution — single registry for content types."""

from __future__ import annotations

from ...models.content_types import ContentType

VISUAL_PROMPT_KEYS: dict[ContentType, str] = {
    ContentType.VIDEO: "content_analyst/visual/video",
    ContentType.IMAGE: "content_analyst/visual/image",
    ContentType.CAROUSEL: "content_analyst/visual/carousel",
}


def resolve_visual_prompt_key(content_type: ContentType) -> str:
    try:
        return VISUAL_PROMPT_KEYS[content_type]
    except KeyError as exc:
        raise ValueError(f"No visual prompt registered for content type: {content_type}") from exc
