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
    ContentAsset,
    ContentFeedback,
    ContentGeneration,
    ContentReview,
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
            vo = scene.voiceover
            voiceover = vo.strip() if vo and vo.strip() else None
            sound_effect = (
                scene.sound_effect.strip()
                if scene.sound_effect and scene.sound_effect.strip()
                else None
            )
            content.scenes.append(
                ContentScene(
                    id=_new_id(),
                    sequence_number=i,
                    start_time=scene.start,
                    end_time=scene.end,
                    scene_description=scene.scene,
                    camera_direction=scene.camera,
                    on_screen_text=scene.text,
                    voiceover=voiceover,
                    sound_effect=sound_effect,
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
        constraints: list[str],
        meta: GenerationMeta,
    ) -> Content:
        content = Content(
            id=_new_id(),
            business_goal=business_goal,
            target_audience=target_audience or idea.target_audience,
            product=product,
            constraints=list(constraints),
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

    def add_version(
        self,
        content: Content,
        *,
        idea: ContentIdea,
        meta: GenerationMeta,
        business_goal: str | None = None,
        target_audience: str | None = None,
        product: str | None = None,
        constraints: list[str] | None = None,
    ) -> Content:
        if business_goal is not None:
            content.business_goal = business_goal
        if target_audience is not None:
            content.target_audience = target_audience or idea.target_audience
        if product is not None:
            content.product = product
        if constraints is not None:
            content.constraints = list(constraints)
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

    def update_performance_notes(self, content: Content, notes: str) -> Content:
        content.performance_notes = notes.strip() or None
        self.session.flush()
        return content

    def add_asset(
        self,
        content_id: str,
        *,
        storage_key: str,
        mime_type: str,
        file_size: int,
        original_filename: str,
    ) -> ContentAsset:
        asset = ContentAsset(
            id=_new_id(),
            content_id=content_id,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=file_size,
            original_filename=original_filename,
        )
        self.session.add(asset)
        self.session.flush()
        return asset

    def get_asset(self, asset_id: str) -> ContentAsset | None:
        return self.session.get(ContentAsset, asset_id)

    def list_assets(self, content_id: str) -> list[ContentAsset]:
        stmt = (
            select(ContentAsset)
            .where(ContentAsset.content_id == content_id)
            .order_by(ContentAsset.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def add_review(
        self,
        content_id: str,
        *,
        review_type: str,
        agent: str,
        payload: dict,
        asset_id: str | None = None,
    ) -> ContentReview:
        review = ContentReview(
            id=_new_id(),
            content_id=content_id,
            asset_id=asset_id,
            review_type=review_type,
            agent=agent,
            payload=payload,
        )
        self.session.add(review)
        self.session.flush()
        return review

    def list_reviews(self, content_id: str) -> list[ContentReview]:
        stmt = (
            select(ContentReview)
            .where(ContentReview.content_id == content_id)
            .order_by(ContentReview.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_past_posts(self, *, exclude_id: str, limit: int = 10) -> list[Content]:
        stmt = (
            select(Content)
            .where(Content.id != exclude_id)
            .where(Content.status.in_(["posted", "analyzed", "promoted"]))
            .order_by(Content.updated_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())
