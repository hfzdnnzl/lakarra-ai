"""Content Management System service.

Orchestrates generation (via the Content Creator agent) plus persistence, status
lifecycle, versioning and feedback. Business logic lives here; the controller only
handles HTTP concerns. The session/transaction is owned by this service.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from ..agents import get_agent_context
from ..agents.content_creator import ContentCreatorAgent
from ..errors import LakarraError
from ..models.content import ContentRequest, ContentResponse
from ..models.db import (
    Content,
    ContentFeedback,
    ContentGeneration,
    ContentStatusHistory,
    ContentVersion,
)
from ..repositories.content_repository import ContentRepository, GenerationMeta

logger = logging.getLogger("lakarra.content_service")


class ContentService:
    def __init__(self, session: Session, agent: ContentCreatorAgent | None = None) -> None:
        self.session = session
        self.repo = ContentRepository(session)
        self._agent = agent or ContentCreatorAgent(get_agent_context())

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
            content = self.repo.add_version(content, idea=result.idea, meta=meta)
        else:
            content = self.repo.create_content(
                idea=result.idea,
                business_goal=request.business_goal,
                target_audience=request.target_audience,
                product=request.product,
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
