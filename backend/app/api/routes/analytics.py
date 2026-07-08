"""Analytics routes — Content Analyst Phase 3."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database.session import get_db
from ...errors import status_for
from ...models.analytics import (
    AccountOverview,
    AnalysisResponse,
    AnalyzeCompetitorRequest,
    AnalyzeVideoRequest,
    CompetitorOverview,
    HistoricalAnalytics,
    ReviewDecisionRequest,
    ReviewQueueItem,
    TrendReportRequest,
)
from ...services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


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
    service: AnalyticsService = Depends(_service),
) -> AnalysisResponse:
    result = service.analyze_video(body.video_id, content_id=body.content_id)
    if not result.success:
        raise HTTPException(status_for(result.error_type), detail=result.error)
    return result


@router.post("/videos/analyze-all")
def analyze_all_videos(service: AnalyticsService = Depends(_service)) -> list[AnalysisResponse]:
    return service.analyze_all_videos()


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
    return service.get_overview()


@router.get("/content")
def get_content_analytics(service: AnalyticsService = Depends(_service)) -> dict:
    overview = service.get_overview()
    historical = service.get_historical()
    return {
        "overview": overview.model_dump(),
        "analyses": [a.model_dump() for a in historical.content_analyses],
    }


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
