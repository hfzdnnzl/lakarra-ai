"""Analytics repository: database access for Content Analyst persistence."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.db import (
    AnalyticsAccountSettingsORM,
    CommentAnalysisORM,
    CompetitorAnalysisORM,
    ContentAnalysisORM,
    MetricsSnapshotORM,
    PatternAnalysisORM,
    ReviewReportORM,
    TrendReportORM,
    VideoMetricsORM,
    VideoUploadORM,
)


def _new_id() -> str:
    return uuid4().hex


class AnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- Account settings --------------------------------------------------
    def get_account_settings(self) -> AnalyticsAccountSettingsORM | None:
        return self.session.get(AnalyticsAccountSettingsORM, "default")

    def set_account_handle(self, handle: str) -> AnalyticsAccountSettingsORM:
        row = self.get_account_settings()
        if row is None:
            row = AnalyticsAccountSettingsORM(id="default", tiktok_handle=handle)
            self.session.add(row)
        else:
            row.tiktok_handle = handle
            # Clear cached snapshot when handle changes
            row.tiktok_snapshot = None
            row.tiktok_snapshot_fetched_at = None
        return row

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

    def get_latest_analysis_for_video(self, video_id: str) -> ContentAnalysisORM | None:
        stmt = (
            select(ContentAnalysisORM)
            .where(ContentAnalysisORM.video_id == video_id)
            .order_by(ContentAnalysisORM.version.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def list_analyzed_video_ids(self) -> set[str]:
        stmt = select(ContentAnalysisORM.video_id).distinct()
        return set(self.session.scalars(stmt))

    def get_latest_analyses_map(self) -> dict[str, ContentAnalysisORM]:
        rows = self.list_content_analyses(limit=500)
        latest: dict[str, ContentAnalysisORM] = {}
        for row in rows:
            if row.video_id not in latest:
                latest[row.video_id] = row
        return latest

    # --- Video metrics (user-editable) -------------------------------------
    def get_video_metrics(self, video_id: str) -> VideoMetricsORM | None:
        stmt = select(VideoMetricsORM).where(VideoMetricsORM.video_id == video_id)
        return self.session.scalar(stmt)

    def upsert_video_metrics(
        self,
        *,
        video_id: str,
        tiktok_handle: str,
        data: dict,
    ) -> VideoMetricsORM:
        row = self.get_video_metrics(video_id)
        if row is None:
            row = VideoMetricsORM(id=_new_id(), video_id=video_id, tiktok_handle=tiktok_handle)
            self.session.add(row)
        for key, value in data.items():
            if hasattr(row, key):
                setattr(row, key, value)
        row.tiktok_handle = tiktok_handle
        return row

    def list_video_metrics(self, *, tiktok_handle: str) -> list[VideoMetricsORM]:
        stmt = select(VideoMetricsORM).where(VideoMetricsORM.tiktok_handle == tiktok_handle)
        return list(self.session.scalars(stmt))

    # --- Video uploads (analytics direct upload) ---------------------------
    def get_video_upload(self, video_id: str) -> VideoUploadORM | None:
        stmt = select(VideoUploadORM).where(VideoUploadORM.video_id == video_id)
        return self.session.scalar(stmt)

    def upsert_video_upload(
        self,
        *,
        video_id: str,
        tiktok_handle: str,
        storage_key: str,
        mime_type: str,
        file_size: int,
        original_filename: str,
    ) -> VideoUploadORM:
        row = self.get_video_upload(video_id)
        if row is None:
            row = VideoUploadORM(
                id=_new_id(),
                video_id=video_id,
                tiktok_handle=tiktok_handle,
                storage_key=storage_key,
                mime_type=mime_type,
                file_size=file_size,
                original_filename=original_filename,
            )
            self.session.add(row)
        else:
            row.tiktok_handle = tiktok_handle
            row.storage_key = storage_key
            row.mime_type = mime_type
            row.file_size = file_size
            row.original_filename = original_filename
        return row

    def delete_video_upload(self, video_id: str) -> VideoUploadORM | None:
        row = self.get_video_upload(video_id)
        if row is None:
            return None
        self.session.delete(row)
        return row

    def list_video_uploads(self, *, tiktok_handle: str) -> list[VideoUploadORM]:
        stmt = select(VideoUploadORM).where(VideoUploadORM.tiktok_handle == tiktok_handle)
        return list(self.session.scalars(stmt))

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

    def list_competitor_handles(self, *, limit: int = 50) -> list[str]:
        stmt = (
            select(CompetitorAnalysisORM.handle)
            .distinct()
            .order_by(CompetitorAnalysisORM.handle)
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

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

    # --- TikTok account snapshot -------------------------------------------
    def get_snapshot(self) -> dict | None:
        """Return the cached TikTok account snapshot (JSON blob), or None."""
        row = self.get_account_settings()
        if row is None:
            return None
        return row.tiktok_snapshot

    def get_snapshot_fetched_at(self):
        """Return the datetime the snapshot was last fetched, or None."""
        row = self.get_account_settings()
        if row is None:
            return None
        return row.tiktok_snapshot_fetched_at

    def save_snapshot(self, data: dict) -> None:
        """Persist a TikTok account snapshot and update the fetched-at timestamp."""
        from datetime import datetime, timezone

        row = self.get_account_settings()
        if row is None:
            row = AnalyticsAccountSettingsORM(id="default")
            self.session.add(row)
        row.tiktok_snapshot = data
        row.tiktok_snapshot_fetched_at = datetime.now(timezone.utc)
