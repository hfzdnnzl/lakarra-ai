"""Content repository: all database access for the CMS.

Keeps SQLAlchemy queries out of the service/controller layers. Methods operate on
an injected :class:`Session`; the caller (service) owns the transaction boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..models.content import ContentIdea
from ..models.db import (
    Content,
    ContentFeedback,
    ContentGeneration,
    ContentScene,
    ContentStatusHistory,
    ContentVersion,
)


def _new_id() -> str:
    return uuid4().hex


@dataclass
class GenerationMeta:
    model_used: str
    prompt_version: str
    temperature: float
    token_usage: dict
    generation_time: float


class ContentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- helpers -----------------------------------------------------------
    def _apply_idea(self, content: Content, idea: ContentIdea) -> None:
        content.title = idea.title
        content.category = str(idea.category)
        content.hook = idea.hook
        content.duration = idea.duration
        content.caption = idea.caption
        content.hashtags = list(idea.hashtags)
        content.cta = idea.cta
        content.posting_time = idea.posting_time
        content.confidence_score = idea.confidence
        content.music_suggestion = idea.music_suggestion

    def _rebuild_scenes(self, content: Content, idea: ContentIdea) -> None:
        content.scenes.clear()
        self.session.flush()
        for i, scene in enumerate(idea.timeline, start=1):
            content.scenes.append(
                ContentScene(
                    id=_new_id(),
                    sequence_number=i,
                    start_time=scene.start,
                    end_time=scene.end,
                    scene_description=scene.scene,
                    camera_direction=scene.camera,
                    on_screen_text=scene.text,
                    voiceover=scene.voiceover,
                    sound_effect=scene.sound_effect,
                )
            )

    def _add_generation(self, content_id: str, meta: GenerationMeta) -> ContentGeneration:
        gen = ContentGeneration(
            id=_new_id(),
            content_id=content_id,
            model_used=meta.model_used,
            prompt_version=meta.prompt_version,
            temperature=meta.temperature,
            token_usage=meta.token_usage,
            generation_time=meta.generation_time,
        )
        self.session.add(gen)
        return gen

    # --- create / regenerate ----------------------------------------------
    def create_content(
        self,
        *,
        idea: ContentIdea,
        business_goal: str,
        target_audience: str,
        product: str,
        meta: GenerationMeta,
    ) -> Content:
        content = Content(
            id=_new_id(),
            business_goal=business_goal,
            target_audience=target_audience or idea.target_audience,
            product=product,
            status="draft",
            active_version=1,
        )
        self._apply_idea(content, idea)
        self.session.add(content)
        self.session.flush()

        self._rebuild_scenes(content, idea)
        content.versions.append(
            ContentVersion(
                id=_new_id(),
                version_number=1,
                hook=idea.hook,
                snapshot=idea.model_dump(mode="json"),
                is_active=True,
            )
        )
        self.session.add(
            ContentStatusHistory(
                id=_new_id(),
                content_id=content.id,
                old_status=None,
                new_status="draft",
                changed_by="system",
                comment="Content created.",
            )
        )
        self._add_generation(content.id, meta)
        self.session.flush()
        return content

    def add_version(self, content: Content, *, idea: ContentIdea, meta: GenerationMeta) -> Content:
        next_number = max((v.version_number for v in content.versions), default=0) + 1
        for version in content.versions:
            version.is_active = False
        self._apply_idea(content, idea)
        self._rebuild_scenes(content, idea)
        content.active_version = next_number
        # Append through the relationship so the in-memory collection stays consistent.
        content.versions.append(
            ContentVersion(
                id=_new_id(),
                version_number=next_number,
                hook=idea.hook,
                snapshot=idea.model_dump(mode="json"),
                is_active=True,
            )
        )
        self._add_generation(content.id, meta)
        self.session.flush()
        return content

    # --- read --------------------------------------------------------------
    def get(self, content_id: str) -> Content | None:
        return self.session.get(Content, content_id)

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        category: str | None = None,
        status: str | None = None,
        sort: str = "-created_at",
    ) -> tuple[list[Content], int]:
        stmt = select(Content)
        if search:
            like = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Content.title).like(like),
                    func.lower(Content.business_goal).like(like),
                    func.lower(Content.hook).like(like),
                )
            )
        if category:
            stmt = stmt.where(Content.category == category)
        if status:
            stmt = stmt.where(Content.status == status)

        total = self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        column = Content.created_at
        if sort.lstrip("-") == "updated_at":
            column = Content.updated_at
        stmt = stmt.order_by(column.desc() if sort.startswith("-") else column.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = list(self.session.scalars(stmt).all())
        return items, total

    def list_versions(self, content_id: str) -> list[ContentVersion]:
        stmt = (
            select(ContentVersion)
            .where(ContentVersion.content_id == content_id)
            .order_by(ContentVersion.version_number.asc())
        )
        return list(self.session.scalars(stmt).all())

    def list_feedback(self, content_id: str) -> list[ContentFeedback]:
        stmt = (
            select(ContentFeedback)
            .where(ContentFeedback.content_id == content_id)
            .order_by(ContentFeedback.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_status_history(self, content_id: str) -> list[ContentStatusHistory]:
        stmt = (
            select(ContentStatusHistory)
            .where(ContentStatusHistory.content_id == content_id)
            .order_by(ContentStatusHistory.changed_at.asc())
        )
        return list(self.session.scalars(stmt).all())

    def list_generations(self, content_id: str) -> list[ContentGeneration]:
        stmt = (
            select(ContentGeneration)
            .where(ContentGeneration.content_id == content_id)
            .order_by(ContentGeneration.created_at.asc())
        )
        return list(self.session.scalars(stmt).all())

    # --- mutate ------------------------------------------------------------
    def update_status(
        self, content: Content, *, new_status: str, changed_by: str, comment: str | None
    ) -> ContentStatusHistory:
        history = ContentStatusHistory(
            id=_new_id(),
            content_id=content.id,
            old_status=content.status,
            new_status=new_status,
            changed_by=changed_by,
            comment=comment,
        )
        content.status = new_status
        self.session.add(history)
        self.session.flush()
        return history

    def activate_version(self, content: Content, version_number: int) -> ContentVersion | None:
        target = next(
            (v for v in content.versions if v.version_number == version_number), None
        )
        if target is None:
            return None
        idea = ContentIdea(**target.snapshot)
        self._apply_idea(content, idea)
        self._rebuild_scenes(content, idea)
        for version in content.versions:
            version.is_active = version.version_number == version_number
        content.active_version = version_number
        self.session.flush()
        return target

    def add_feedback(self, content_id: str, *, message: str, created_by: str) -> ContentFeedback:
        feedback = ContentFeedback(
            id=_new_id(), content_id=content_id, message=message, created_by=created_by
        )
        self.session.add(feedback)
        self.session.flush()
        return feedback
