"""Content Management System service.

Orchestrates generation (via the Content Creator agent) plus persistence, status
lifecycle, versioning and feedback. Business logic lives here; the controller only
handles HTTP concerns. The session/transaction is owned by this service.
"""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from sqlalchemy.orm import Session

from ..agents import get_agent_context
from ..agents.content_analyst import ContentAnalystAgent
from ..agents.content_creator import ContentCreatorAgent
from ..config import get_settings
from ..errors import LakarraError
from ..models.content import ContentRequest, ContentResponse, ReviewResponse
from ..models.db import (
    Content,
    ContentAsset,
    ContentFeedback,
    ContentGeneration,
    ContentReview,
    ContentStatusHistory,
    ContentVersion,
)
from ..repositories.content_repository import ContentRepository, GenerationMeta
from ..services.storage_service import get_storage

logger = logging.getLogger("lakarra.content_service")


class ContentService:
    def __init__(
        self,
        session: Session,
        agent: ContentCreatorAgent | None = None,
        analyst: ContentAnalystAgent | None = None,
    ) -> None:
        self.session = session
        self.repo = ContentRepository(session)
        ctx = get_agent_context()
        self._agent = agent or ContentCreatorAgent(ctx)
        self._analyst = analyst or ContentAnalystAgent(ctx)

    # --- generate / regenerate --------------------------------------------
    def generate(
        self,
        request: ContentRequest,
        *,
        content_id: str | None = None,
        temperature: float = 0.7,
    ) -> ContentResponse:
        logger.info(
            "content.generate goal=%r regenerate=%s", request.business_goal, bool(content_id)
        )

        started = time.perf_counter()
        try:
            result = self._agent.generate(request, temperature=temperature)
        except LakarraError as exc:
            logger.warning("content.generate.failed type=%s error=%s", exc.error_type, exc.message)
            return ContentResponse(success=False, error=exc.message, error_type=exc.error_type)
        except Exception as exc:  # noqa: BLE001 - never leak raw tracebacks
            logger.exception("content.generate.unexpected")
            return ContentResponse(success=False, error=str(exc), error_type="error")

        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        meta = GenerationMeta(
            model_used=result.model,
            prompt_version=result.prompt_version,
            temperature=temperature,
            token_usage=result.usage,
            generation_time=elapsed_ms,
        )

        if content_id:
            content = self.repo.get(content_id)
            if content is None:
                return ContentResponse(
                    success=False, error="Content not found.", error_type="not_found"
                )
            content = self.repo.add_version(
                content,
                idea=result.idea,
                meta=meta,
                business_goal=request.business_goal,
                target_audience=request.target_audience,
                product=request.product,
                constraints=request.constraints,
            )
        else:
            content = self.repo.create_content(
                idea=result.idea,
                business_goal=request.business_goal,
                target_audience=request.target_audience,
                product=request.product,
                constraints=request.constraints,
                meta=meta,
            )

        self.session.commit()
        logger.info(
            "content.generate.saved content_id=%s version=%s model=%s prompt_version=%s "
            "elapsed_ms=%s usage=%s",
            content.id,
            content.active_version,
            result.model,
            result.prompt_version,
            elapsed_ms,
            result.usage,
        )
        return ContentResponse(success=True, data=result.idea, content_id=content.id)

    # --- reads -------------------------------------------------------------
    def get(self, content_id: str) -> Content | None:
        return self.repo.get(content_id)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        category: str | None,
        status: str | None,
        sort: str,
    ) -> tuple[list[Content], int]:
        return self.repo.list(
            page=page,
            page_size=page_size,
            search=search,
            category=category,
            status=status,
            sort=sort,
        )

    def versions(self, content_id: str) -> list[ContentVersion]:
        return self.repo.list_versions(content_id)

    def feedback(self, content_id: str) -> list[ContentFeedback]:
        return self.repo.list_feedback(content_id)

    def status_history(self, content_id: str) -> list[ContentStatusHistory]:
        return self.repo.list_status_history(content_id)

    def generations(self, content_id: str) -> list[ContentGeneration]:
        return self.repo.list_generations(content_id)

    # --- mutations ---------------------------------------------------------
    def update_status(
        self, content_id: str, *, new_status: str, changed_by: str, comment: str | None
    ) -> Content | None:
        content = self.repo.get(content_id)
        if content is None:
            return None
        self.repo.update_status(
            content, new_status=new_status, changed_by=changed_by, comment=comment
        )
        self.session.commit()
        return content

    def activate_version(self, content_id: str, version_number: int) -> Content | None:
        content = self.repo.get(content_id)
        if content is None:
            return None
        activated = self.repo.activate_version(content, version_number)
        if activated is None:
            return None
        self.session.commit()
        return content

    def add_feedback(
        self, content_id: str, *, message: str, created_by: str
    ) -> ContentFeedback | None:
        if self.repo.get(content_id) is None:
            return None
        feedback = self.repo.add_feedback(content_id, message=message, created_by=created_by)
        self.session.commit()
        return feedback

    def update_performance_notes(self, content_id: str, notes: str) -> Content | None:
        content = self.repo.get(content_id)
        if content is None:
            return None
        self.repo.update_performance_notes(content, notes)
        self.session.commit()
        return content

    def upload_asset(
        self,
        content_id: str,
        *,
        data: bytes,
        mime_type: str,
        original_filename: str,
    ) -> ContentAsset | None:
        settings = get_settings()
        if len(data) > settings.max_upload_bytes:
            raise ValueError(
                f"File exceeds maximum size of {settings.max_upload_bytes // (1024 * 1024)} MB."
            )
        if mime_type not in settings.allowed_upload_mime_types:
            raise ValueError(f"Unsupported file type: {mime_type}")

        content = self.repo.get(content_id)
        if content is None:
            return None

        storage_key = f"content/{content_id}/{uuid4().hex}_{original_filename}"
        get_storage().put_object(storage_key, data, content_type=mime_type)
        asset = self.repo.add_asset(
            content_id,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=len(data),
            original_filename=original_filename,
        )
        if content.status in ("draft", "approved"):
            self.repo.update_status(
                content,
                new_status="filming",
                changed_by="user",
                comment="Video uploaded.",
            )
        self.session.commit()
        return asset

    def list_assets(self, content_id: str) -> list[ContentAsset]:
        return self.repo.list_assets(content_id)

    def get_asset(self, asset_id: str) -> ContentAsset | None:
        return self.repo.get_asset(asset_id)

    def read_asset_bytes(self, asset: ContentAsset) -> bytes:
        return get_storage().read_object(asset.storage_key)

    def list_reviews(self, content_id: str) -> list[ContentReview]:
        return self.repo.list_reviews(content_id)

    def run_review(self, content_id: str, *, asset_id: str) -> ReviewResponse:
        content = self.repo.get(content_id)
        if content is None:
            return ReviewResponse(success=False, error="Content not found.", error_type="not_found")

        asset = self.repo.get_asset(asset_id)
        if asset is None or asset.content_id != content_id:
            return ReviewResponse(
                success=False, error="Asset not found.", error_type="not_found"
            )

        try:
            video_bytes = self.read_asset_bytes(asset)
            fidelity_result = self._agent.review_asset(
                content, video_bytes=video_bytes, mime_type=asset.mime_type
            )
            past_posts = self.repo.list_past_posts(exclude_id=content_id)
            performance_result = self._analyst.analyze_asset(
                content,
                video_bytes=video_bytes,
                mime_type=asset.mime_type,
                past_posts=past_posts,
            )
        except LakarraError as exc:
            logger.warning("content.review.failed type=%s error=%s", exc.error_type, exc.message)
            return ReviewResponse(success=False, error=exc.message, error_type=exc.error_type)
        except Exception as exc:  # noqa: BLE001
            logger.exception("content.review.unexpected")
            return ReviewResponse(success=False, error=str(exc), error_type="error")

        self.repo.add_review(
            content_id,
            review_type="fidelity",
            agent=self._agent.name,
            payload=fidelity_result.review.model_dump(mode="json"),
            asset_id=asset_id,
        )
        self.repo.add_review(
            content_id,
            review_type="performance",
            agent=self._analyst.name,
            payload=performance_result.review.model_dump(mode="json"),
            asset_id=asset_id,
        )
        if content.status in ("filming", "editing", "posted"):
            self.repo.update_status(
                content,
                new_status="analyzed",
                changed_by="system",
                comment="Automated review completed.",
            )
        self.session.commit()

        return ReviewResponse(
            success=True,
            fidelity=fidelity_result.review,
            performance=performance_result.review,
        )
