"""Analytics routes — Content Analyst Phase 3."""

from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from ...database.session import get_db
from ...errors import status_for
from ...models.analytics import (
    AccountOverview,
    AccountSettingsRead,
    AccountSettingsUpdate,
    AnalysisResponse,
    AnalyzeAllResponse,
    AnalyzeCompetitorRequest,
    AnalyzeContentRequest,
    AnalyzeVideoRequest,
    CompetitorOverview,
    ContentAnalyticsPage,
    HistoricalAnalytics,
    MetricsReadiness,
    ReviewDecisionRequest,
    ReviewQueueItem,
    TrendReportRequest,
    VideoMetricsData,
    VideoMetricsRead,
    VideoUploadRead,
)
from ...services.analytics_service import AnalyticsService
from ...services.storage_service import get_storage

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


# --- Account settings --------------------------------------------------------
@router.get("/account/settings", response_model=AccountSettingsRead)
def get_account_settings(service: AnalyticsService = Depends(_service)) -> AccountSettingsRead:
    return service.get_account_settings()


@router.put("/account/settings", response_model=AccountSettingsRead)
def update_account_settings(
    body: AccountSettingsUpdate,
    service: AnalyticsService = Depends(_service),
) -> AccountSettingsRead:
    try:
        return service.set_account_handle(body.tiktok_handle)
    except Exception as exc:
        from ...errors import LakarraError

        if isinstance(exc, LakarraError):
            raise HTTPException(status_for(exc.error_type), detail=exc.message) from exc
        raise


# --- Analysis triggers -------------------------------------------------------
@router.post("/account/analyze", response_model=AnalysisResponse)
def analyze_account(service: AnalyticsService = Depends(_service)) -> AnalysisResponse:
    result = service.analyze_account()
    if not result.success:
        raise HTTPException(status_for(result.error_type), detail=result.error)
    return result


@router.post("/videos/analyze", response_model=AnalysisResponse)
def analyze_video(
    body: AnalyzeVideoRequest,
    force: bool = False,
    service: AnalyticsService = Depends(_service),
) -> AnalysisResponse:
    result = service.analyze_content(
        body.video_id,
        content_id=body.content_id,
        force=force,
    )
    if not result.success:
        raise HTTPException(status_for(result.error_type), detail=result.error)
    return result


@router.post("/content/{post_id}/analyze", response_model=AnalysisResponse)
def analyze_content(
    post_id: str,
    body: AnalyzeContentRequest | None = None,
    force: bool = False,
    service: AnalyticsService = Depends(_service),
) -> AnalysisResponse:
    req = body or AnalyzeContentRequest()
    result = service.analyze_content(
        post_id,
        content_id=req.content_id,
        content_type=req.content_type,
        force=force,
    )
    if not result.success and not result.skipped:
        raise HTTPException(status_for(result.error_type), detail=result.error)
    return result


@router.post("/videos/{video_id}/analyze", response_model=AnalysisResponse)
def analyze_video_by_id(
    video_id: str,
    force: bool = False,
    service: AnalyticsService = Depends(_service),
) -> AnalysisResponse:
    result = service.analyze_content(video_id, force=force)
    if not result.success and not result.skipped:
        raise HTTPException(status_for(result.error_type), detail=result.error)
    return result


@router.post("/videos/{video_id}/upload", response_model=VideoUploadRead, status_code=201)
async def upload_video(
    video_id: str,
    file: UploadFile = File(...),
    service: AnalyticsService = Depends(_service),
) -> VideoUploadRead:
    data = await file.read()
    mime = file.content_type or "application/octet-stream"
    try:
        return service.upload_video_file(
            video_id,
            data=data,
            mime_type=mime,
            original_filename=file.filename or "upload.mp4",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        from ...errors import LakarraError

        if isinstance(exc, LakarraError):
            raise HTTPException(status_for(exc.error_type), detail=exc.message) from exc
        raise


@router.get("/videos/{video_id}/upload/stream")
def stream_video_upload(
    video_id: str,
    service: AnalyticsService = Depends(_service),
):
    row = service.get_video_upload_row(video_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    local_path = get_storage().get_local_path(row.storage_key)
    if local_path is not None:
        return FileResponse(
            local_path,
            media_type=row.mime_type,
            filename=row.original_filename,
            content_disposition_type="inline",
        )
    try:
        data = get_storage().read_object(row.storage_key)
    except OSError as exc:
        raise HTTPException(status_code=404, detail="Upload file not found") from exc
    return StreamingResponse(
        BytesIO(data),
        media_type=row.mime_type,
        headers={"Content-Disposition": f'inline; filename="{row.original_filename}"'},
    )


@router.delete("/videos/{video_id}/upload", status_code=204)
def delete_video_upload(
    video_id: str,
    service: AnalyticsService = Depends(_service),
) -> None:
    try:
        service.delete_video_upload(video_id)
    except Exception as exc:
        from ...errors import LakarraError

        if isinstance(exc, LakarraError):
            raise HTTPException(status_for(exc.error_type), detail=exc.message) from exc
        raise


@router.post("/videos/analyze-all", response_model=AnalyzeAllResponse)
def analyze_all_videos(service: AnalyticsService = Depends(_service)) -> AnalyzeAllResponse:
    try:
        return service.analyze_all_videos()
    except Exception as exc:
        from ...errors import LakarraError

        if isinstance(exc, LakarraError):
            raise HTTPException(status_for(exc.error_type), detail=exc.message) from exc
        raise


@router.put("/videos/{video_id}/metrics", response_model=VideoMetricsRead)
def update_video_metrics(
    video_id: str,
    body: VideoMetricsData,
    service: AnalyticsService = Depends(_service),
) -> VideoMetricsRead:
    try:
        return service.update_video_metrics(video_id, body)
    except Exception as exc:
        from ...errors import LakarraError

        if isinstance(exc, LakarraError):
            raise HTTPException(status_for(exc.error_type), detail=exc.message) from exc
        raise


@router.get("/metrics/readiness", response_model=MetricsReadiness)
def get_metrics_readiness(service: AnalyticsService = Depends(_service)) -> MetricsReadiness:
    try:
        return service.get_metrics_readiness()
    except Exception as exc:
        from ...errors import LakarraError

        if isinstance(exc, LakarraError):
            raise HTTPException(status_for(exc.error_type), detail=exc.message) from exc
        raise


@router.post("/competitors/analyze", response_model=AnalysisResponse)
def analyze_competitor(
    body: AnalyzeCompetitorRequest,
    service: AnalyticsService = Depends(_service),
) -> AnalysisResponse:
    result = service.analyze_competitor(body.handle)
    if not result.success:
        raise HTTPException(status_for(result.error_type), detail=result.error)
    return result


@router.post("/content/{content_id}/review", response_model=AnalysisResponse)
def review_content(
    content_id: str,
    service: AnalyticsService = Depends(_service),
) -> AnalysisResponse:
    result = service.review_content(content_id)
    if not result.success:
        raise HTTPException(status_for(result.error_type), detail=result.error)
    return result


@router.post("/trends/generate", response_model=AnalysisResponse)
def generate_trend_report(
    body: TrendReportRequest | None = None,
    service: AnalyticsService = Depends(_service),
) -> AnalysisResponse:
    period = body.period if body else "30d"
    result = service.generate_trend_report(period=period)
    if not result.success:
        raise HTTPException(status_for(result.error_type), detail=result.error)
    return result


# --- Review decisions --------------------------------------------------------
@router.post("/reviews/{report_id}/decision", response_model=AnalysisResponse)
def decide_review(
    report_id: str,
    body: ReviewDecisionRequest,
    service: AnalyticsService = Depends(_service),
) -> AnalysisResponse:
    result = service.decide_review(
        report_id,
        decision=body.decision,
        comment=body.comment,
        decided_by=body.decided_by,
    )
    if not result.success:
        raise HTTPException(status_for(result.error_type), detail=result.error)
    return result


# --- Dashboard reads ---------------------------------------------------------
@router.get("/overview", response_model=AccountOverview)
def get_overview(service: AnalyticsService = Depends(_service)) -> AccountOverview:
    try:
        return service.get_overview()
    except Exception as exc:
        from ...errors import LakarraError

        if isinstance(exc, LakarraError):
            raise HTTPException(status_for(exc.error_type), detail=exc.message) from exc
        raise


SORT_BY_VALUES = ["publish_date", "views", "likes"]
SORT_ORDER_VALUES = ["asc", "desc"]


@router.get("/content", response_model=ContentAnalyticsPage)
def get_content_analytics(
    service: AnalyticsService = Depends(_service),
    sort_by: str = Query("publish_date", description="Sort field"),
    sort_order: str = Query("desc", description="asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
) -> ContentAnalyticsPage:
    if sort_by not in SORT_BY_VALUES:
        sort_by = "publish_date"
    if sort_order not in SORT_ORDER_VALUES:
        sort_order = "desc"
    try:
        return service.get_content_page(
            sort_by=sort_by, sort_order=sort_order, page=page, per_page=per_page
        )
    except Exception as exc:
        from ...errors import LakarraError

        if isinstance(exc, LakarraError):
            raise HTTPException(status_for(exc.error_type), detail=exc.message) from exc
        raise


@router.post("/content/refresh", response_model=ContentAnalyticsPage)
def refresh_content_analytics(
    service: AnalyticsService = Depends(_service),
    sort_by: str = Query("publish_date", description="Sort field"),
    sort_order: str = Query("desc", description="asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
) -> ContentAnalyticsPage:
    """Force a live TikTok fetch, update the DB snapshot, and return the page."""
    if sort_by not in SORT_BY_VALUES:
        sort_by = "publish_date"
    if sort_order not in SORT_ORDER_VALUES:
        sort_order = "desc"
    try:
        return service.refresh_content_page(
            sort_by=sort_by, sort_order=sort_order, page=page, per_page=per_page
        )
    except Exception as exc:
        from ...errors import LakarraError

        if isinstance(exc, LakarraError):
            raise HTTPException(status_for(exc.error_type), detail=exc.message) from exc
        raise


@router.get("/competitors", response_model=CompetitorOverview)
def get_competitor_analytics(
    service: AnalyticsService = Depends(_service),
) -> CompetitorOverview:
    return service.get_competitor_overview()


@router.get("/trends")
def get_trend_reports(service: AnalyticsService = Depends(_service)) -> dict:
    historical = service.get_historical()
    return {"reports": [r.model_dump() for r in historical.trend_reports]}


@router.get("/review-queue", response_model=list[ReviewQueueItem])
def get_review_queue(service: AnalyticsService = Depends(_service)) -> list[ReviewQueueItem]:
    return service.get_review_queue()


@router.get("/historical", response_model=HistoricalAnalytics)
def get_historical(service: AnalyticsService = Depends(_service)) -> HistoricalAnalytics:
    return service.get_historical()


# --- Legacy endpoint (metrics snapshots) -------------------------------------
@router.get("")
def list_metrics(service: AnalyticsService = Depends(_service)) -> list[dict]:
    historical = service.get_historical()
    return [s.model_dump(mode="json") for s in historical.metrics_snapshots]


@router.post("/content/{post_id}/analysis/prune")
def prune_content_analyses(
    post_id: str,
    service: AnalyticsService = Depends(_service),
) -> dict:
    """Delete all analysis versions for a video except the latest one."""
    from ...errors import NotFoundError as LakarraNotFoundError

    try:
        deleted = service.prune_old_analyses(post_id)
        return {"deleted": deleted}
    except LakarraNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
