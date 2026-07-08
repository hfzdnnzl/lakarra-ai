"""Content Management System API (Phase 2.5).

Controller layer only: HTTP concerns + serialization. All business logic lives in
:class:`ContentService`.
"""

from __future__ import annotations

from math import ceil

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...errors import status_for
from ...models.content import (
    ContentAssetRead,
    ContentRead,
    ContentReviewRead,
    ContentSummary,
    ContentVersionRead,
    FeedbackRead,
    FeedbackRequest,
    GenerateRequest,
    GenerationRead,
    PaginatedContents,
    PerformanceNotesRequest,
    ReviewResponse,
    StatusHistoryRead,
    StatusUpdateRequest,
)
from ...services.content_service import ContentService
from ...services.storage_service import get_storage

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


# --- assets / upload -------------------------------------------------------
@router.get("/{content_id}/assets", response_model=list[ContentAssetRead])
def list_assets(
    content_id: str, service: ContentService = Depends(_service)
) -> list[ContentAssetRead]:
    _get_or_404(service, content_id)
    return [ContentAssetRead.model_validate(a) for a in service.list_assets(content_id)]


@router.post("/{content_id}/assets", response_model=ContentAssetRead, status_code=201)
async def upload_asset(
    content_id: str,
    file: UploadFile = File(...),
    service: ContentService = Depends(_service),
) -> ContentAssetRead:
    _get_or_404(service, content_id)
    data = await file.read()
    mime = file.content_type or "application/octet-stream"
    try:
        asset = service.upload_asset(
            content_id,
            data=data,
            mime_type=mime,
            original_filename=file.filename or "upload.mp4",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if asset is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return ContentAssetRead.model_validate(asset)


@router.get("/{content_id}/assets/{asset_id}/stream")
def stream_asset(
    content_id: str, asset_id: str, service: ContentService = Depends(_service)
):
    _get_or_404(service, content_id)
    asset = service.get_asset(asset_id)
    if asset is None or asset.content_id != content_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    local_path = get_storage().get_local_path(asset.storage_key)
    if local_path is None:
        raise HTTPException(status_code=404, detail="Asset file not available locally")
    return FileResponse(local_path, media_type=asset.mime_type, filename=asset.original_filename)


# --- review ----------------------------------------------------------------
@router.post("/{content_id}/review", response_model=ReviewResponse)
def run_review(
    content_id: str,
    asset_id: str = Query(..., description="Uploaded asset to review"),
    service: ContentService = Depends(_service),
) -> ReviewResponse:
    _get_or_404(service, content_id)
    response = service.run_review(content_id, asset_id=asset_id)
    if not response.success and response.error_type == "not_found":
        raise HTTPException(status_code=404, detail=response.error or "Not found")
    return response


@router.get("/{content_id}/reviews", response_model=list[ContentReviewRead])
def list_reviews(
    content_id: str, service: ContentService = Depends(_service)
) -> list[ContentReviewRead]:
    _get_or_404(service, content_id)
    return [ContentReviewRead.model_validate(r) for r in service.list_reviews(content_id)]


# --- performance notes (past post context) ---------------------------------
@router.patch("/{content_id}/performance-notes", response_model=ContentRead)
def update_performance_notes(
    content_id: str,
    body: PerformanceNotesRequest,
    service: ContentService = Depends(_service),
) -> ContentRead:
    content = service.update_performance_notes(content_id, body.performance_notes)
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return ContentRead.model_validate(content)
