"""Analytics repository: database access for Content Analyst persistence."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.db import (
    CommentAnalysisORM,
    CompetitorAnalysisORM,
    ContentAnalysisORM,
    MetricsSnapshotORM,
    PatternAnalysisORM,
    ReviewReportORM,
    TrendReportORM,
)


def _new_id() -> str:
    return uuid4().hex


class AnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _next_version(self, model: type, **filters) -> int:
        stmt = select(func.coalesce(func.max(model.version), 0)).where(
            *[getattr(model, k) == v for k, v in filters.items()]
        )
        current = self.session.scalar(stmt) or 0
        return current + 1

    # --- Content Analysis --------------------------------------------------
    def save_content_analysis(
        self,
        *,
        video_id: str,
        content_id: str | None,
        version: int,
        agent: str,
        provider: str,
        model: str,
        prompt_version: str,
        payload: dict,
    ) -> ContentAnalysisORM:
        row = ContentAnalysisORM(
            id=_new_id(),
            video_id=video_id,
            content_id=content_id,
            version=version,
            agent=agent,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            payload=payload,
        )
        self.session.add(row)
        return row

    def next_content_analysis_version(self, video_id: str) -> int:
        return self._next_version(ContentAnalysisORM, video_id=video_id)

    def list_content_analyses(
        self, *, video_id: str | None = None, limit: int = 50
    ) -> list[ContentAnalysisORM]:
        stmt = select(ContentAnalysisORM).order_by(ContentAnalysisORM.created_at.desc())
        if video_id:
            stmt = stmt.where(ContentAnalysisORM.video_id == video_id)
        return list(self.session.scalars(stmt.limit(limit)))

    def get_content_analysis(self, analysis_id: str) -> ContentAnalysisORM | None:
        return self.session.get(ContentAnalysisORM, analysis_id)

    # --- Competitor Analysis -----------------------------------------------
    def save_competitor_analysis(
        self,
        *,
        handle: str,
        version: int,
        agent: str,
        provider: str,
        model: str,
        prompt_version: str,
        payload: dict,
    ) -> CompetitorAnalysisORM:
        row = CompetitorAnalysisORM(
            id=_new_id(),
            handle=handle,
            version=version,
            agent=agent,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            payload=payload,
        )
        self.session.add(row)
        return row

    def next_competitor_version(self, handle: str) -> int:
        return self._next_version(CompetitorAnalysisORM, handle=handle)

    def list_competitor_analyses(
        self, *, handle: str | None = None, limit: int = 50
    ) -> list[CompetitorAnalysisORM]:
        stmt = select(CompetitorAnalysisORM).order_by(
            CompetitorAnalysisORM.created_at.desc()
        )
        if handle:
            stmt = stmt.where(CompetitorAnalysisORM.handle == handle)
        return list(self.session.scalars(stmt.limit(limit)))

    # --- Trend Reports -----------------------------------------------------
    def save_trend_report(
        self,
        *,
        period: str,
        version: int,
        agent: str,
        provider: str,
        model: str,
        prompt_version: str,
        payload: dict,
    ) -> TrendReportORM:
        row = TrendReportORM(
            id=_new_id(),
            period=period,
            version=version,
            agent=agent,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            payload=payload,
        )
        self.session.add(row)
        return row

    def next_trend_version(self, period: str) -> int:
        return self._next_version(TrendReportORM, period=period)

    def list_trend_reports(self, *, limit: int = 20) -> list[TrendReportORM]:
        stmt = (
            select(TrendReportORM)
            .order_by(TrendReportORM.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    # --- Review Reports ----------------------------------------------------
    def save_review_report(
        self,
        *,
        content_id: str,
        version: int,
        agent: str,
        provider: str,
        model: str,
        prompt_version: str,
        payload: dict,
    ) -> ReviewReportORM:
        row = ReviewReportORM(
            id=_new_id(),
            content_id=content_id,
            version=version,
            agent=agent,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            payload=payload,
        )
        self.session.add(row)
        return row

    def next_review_version(self, content_id: str) -> int:
        return self._next_version(ReviewReportORM, content_id=content_id)

    def list_review_reports(
        self, *, content_id: str | None = None, limit: int = 50
    ) -> list[ReviewReportORM]:
        stmt = select(ReviewReportORM).order_by(ReviewReportORM.created_at.desc())
        if content_id:
            stmt = stmt.where(ReviewReportORM.content_id == content_id)
        return list(self.session.scalars(stmt.limit(limit)))

    def get_review_report(self, report_id: str) -> ReviewReportORM | None:
        return self.session.get(ReviewReportORM, report_id)

    def update_review_decision(
        self,
        report: ReviewReportORM,
        *,
        decision: str,
        comment: str | None,
        decided_by: str,
    ) -> ReviewReportORM:
        from datetime import UTC, datetime

        report.decision = decision
        report.decision_comment = comment
        report.decided_by = decided_by
        report.decided_at = datetime.now(UTC)
        return report

    def latest_review_for_content(self, content_id: str) -> ReviewReportORM | None:
        stmt = (
            select(ReviewReportORM)
            .where(ReviewReportORM.content_id == content_id)
            .order_by(ReviewReportORM.version.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    # --- Comment Analysis --------------------------------------------------
    def save_comment_analysis(
        self,
        *,
        video_id: str,
        version: int,
        agent: str,
        provider: str,
        model: str,
        prompt_version: str,
        payload: dict,
    ) -> CommentAnalysisORM:
        row = CommentAnalysisORM(
            id=_new_id(),
            video_id=video_id,
            version=version,
            agent=agent,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            payload=payload,
        )
        self.session.add(row)
        return row

    def next_comment_version(self, video_id: str) -> int:
        return self._next_version(CommentAnalysisORM, video_id=video_id)

    # --- Pattern Analysis --------------------------------------------------
    def save_pattern_analysis(
        self,
        *,
        subject_id: str,
        version: int,
        agent: str,
        provider: str,
        model: str,
        prompt_version: str,
        payload: dict,
    ) -> PatternAnalysisORM:
        row = PatternAnalysisORM(
            id=_new_id(),
            subject_id=subject_id,
            version=version,
            agent=agent,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            payload=payload,
        )
        self.session.add(row)
        return row

    def next_pattern_version(self, subject_id: str) -> int:
        return self._next_version(PatternAnalysisORM, subject_id=subject_id)

    def list_pattern_analyses(self, *, limit: int = 20) -> list[PatternAnalysisORM]:
        stmt = (
            select(PatternAnalysisORM)
            .order_by(PatternAnalysisORM.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    # --- Metrics Snapshots -------------------------------------------------
    def save_metrics_snapshot(
        self,
        *,
        metric: str,
        value: float,
        dimension: str | None = None,
        context: dict | None = None,
    ) -> MetricsSnapshotORM:
        row = MetricsSnapshotORM(
            id=_new_id(),
            metric=metric,
            value=value,
            dimension=dimension,
            context=context or {},
        )
        self.session.add(row)
        return row

    def list_metrics_snapshots(self, *, limit: int = 100) -> list[MetricsSnapshotORM]:
        stmt = (
            select(MetricsSnapshotORM)
            .order_by(MetricsSnapshotORM.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))
