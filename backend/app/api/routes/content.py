"""Content Management System API (Phase 2.5).

Controller layer only: HTTP concerns + serialization. All business logic lives in
:class:`ContentService`.
"""

from __future__ import annotations

from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...errors import status_for
from ...models.content import (
    ContentRead,
    ContentSummary,
    ContentVersionRead,
    FeedbackRead,
    FeedbackRequest,
    GenerateRequest,
    GenerationRead,
    PaginatedContents,
    StatusHistoryRead,
    StatusUpdateRequest,
)
from ...services.content_service import ContentService

router = APIRouter(prefix="/content", tags=["content"])


def _service(db: Session = Depends(get_db)) -> ContentService:
    return ContentService(db)


def _get_or_404(service: ContentService, content_id: str):
    content = service.get(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


# --- generate / regenerate -------------------------------------------------
@router.post("/generate")
def generate_content(
    body: GenerateRequest, service: ContentService = Depends(_service)
) -> JSONResponse:
    """Generate a content plan, persist it (content + scenes + metadata), and
    return the saved content id. Pass ``content_id`` to create a new version."""

    response = service.generate(
        body,
        content_id=body.content_id,
        temperature=body.temperature,
    )
    status_code = 200 if response.success else status_for(response.error_type)
    return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"))


# --- library / detail ------------------------------------------------------
@router.get("", response_model=PaginatedContents)
def list_content(
    service: ContentService = Depends(_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = None,
    category: str | None = None,
    status: str | None = None,
    sort: str = "-created_at",
) -> PaginatedContents:
    items, total = service.list(
        page=page,
        page_size=page_size,
        search=search,
        category=category,
        status=status,
        sort=sort,
    )
    return PaginatedContents(
        items=[ContentSummary.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if page_size else 0,
    )


@router.get("/{content_id}", response_model=ContentRead)
def get_content(content_id: str, service: ContentService = Depends(_service)) -> ContentRead:
    return ContentRead.model_validate(_get_or_404(service, content_id))


# --- status lifecycle ------------------------------------------------------
@router.patch("/{content_id}/status", response_model=ContentRead)
def update_status(
    content_id: str, body: StatusUpdateRequest, service: ContentService = Depends(_service)
) -> ContentRead:
    content = service.update_status(
        content_id,
        new_status=body.status.value,
        changed_by=body.changed_by,
        comment=body.comment,
    )
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return ContentRead.model_validate(content)


@router.get("/{content_id}/history", response_model=list[StatusHistoryRead])
def status_history(
    content_id: str, service: ContentService = Depends(_service)
) -> list[StatusHistoryRead]:
    _get_or_404(service, content_id)
    return [StatusHistoryRead.model_validate(h) for h in service.status_history(content_id)]


# --- versioning ------------------------------------------------------------
@router.get("/{content_id}/versions", response_model=list[ContentVersionRead])
def list_versions(
    content_id: str, service: ContentService = Depends(_service)
) -> list[ContentVersionRead]:
    _get_or_404(service, content_id)
    return [ContentVersionRead.model_validate(v) for v in service.versions(content_id)]


@router.post("/{content_id}/versions/{version_number}/activate", response_model=ContentRead)
def activate_version(
    content_id: str, version_number: int, service: ContentService = Depends(_service)
) -> ContentRead:
    content = service.activate_version(content_id, version_number)
    if content is None:
        raise HTTPException(status_code=404, detail="Content or version not found")
    return ContentRead.model_validate(content)


# --- feedback --------------------------------------------------------------
@router.post("/{content_id}/feedback", response_model=FeedbackRead, status_code=201)
def add_feedback(
    content_id: str, body: FeedbackRequest, service: ContentService = Depends(_service)
) -> FeedbackRead:
    feedback = service.add_feedback(
        content_id, message=body.message, created_by=body.created_by
    )
    if feedback is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return FeedbackRead.model_validate(feedback)


@router.get("/{content_id}/feedback", response_model=list[FeedbackRead])
def list_feedback(
    content_id: str, service: ContentService = Depends(_service)
) -> list[FeedbackRead]:
    _get_or_404(service, content_id)
    return [FeedbackRead.model_validate(f) for f in service.feedback(content_id)]


# --- generation metadata ---------------------------------------------------
@router.get("/{content_id}/generations", response_model=list[GenerationRead])
def list_generations(
    content_id: str, service: ContentService = Depends(_service)
) -> list[GenerationRead]:
    _get_or_404(service, content_id)
    return [GenerationRead.model_validate(g) for g in service.generations(content_id)]
