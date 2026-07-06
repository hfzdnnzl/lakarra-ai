"""Content Creator service layer.

Business logic lives here, not in the API controller. The service orchestrates the
agent, measures response time, logs request/model/prompt-version/usage/errors, and
translates failures into a structured :class:`ContentResponse`.
"""

from __future__ import annotations

import logging
import time

from ..agents import get_agent_context
from ..agents.content_creator import ContentCreatorAgent
from ..errors import LakarraError
from ..models.content import ContentRequest, ContentResponse

logger = logging.getLogger("lakarra.content_creator")


class ContentCreatorService:
    """Orchestrates content generation for the API."""

    def __init__(self, agent: ContentCreatorAgent | None = None) -> None:
        self._agent = agent or ContentCreatorAgent(get_agent_context())

    def generate(self, request: ContentRequest) -> ContentResponse:
        logger.info(
            "content.generate.request goal=%r audience=%r product=%r constraints=%s",
            request.business_goal,
            request.target_audience,
            request.product,
            request.constraints,
        )

        started = time.perf_counter()
        try:
            result = self._agent.generate(request)
        except LakarraError as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            logger.warning(
                "content.generate.failed type=%s elapsed_ms=%s error=%s",
                exc.error_type,
                elapsed_ms,
                exc.message,
            )
            return ContentResponse(success=False, error=exc.message, error_type=exc.error_type)
        except Exception as exc:  # noqa: BLE001 - never leak raw tracebacks to clients
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            logger.exception("content.generate.unexpected elapsed_ms=%s", elapsed_ms)
            return ContentResponse(success=False, error=str(exc), error_type="error")

        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        logger.info(
            "content.generate.success model=%s provider=%s prompt_version=%s "
            "elapsed_ms=%s usage=%s",
            result.model,
            result.provider,
            result.prompt_version,
            elapsed_ms,
            result.usage,
        )
        return ContentResponse(success=True, data=result.idea)
