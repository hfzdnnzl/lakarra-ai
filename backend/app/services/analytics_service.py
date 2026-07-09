"""Analytics service — orchestrates Content Analyst agent and persistence."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from ..agents import get_agent_context
from ..agents.content_analyst import ContentAnalystAgent
from ..config import effective_video_analysis_model, effective_video_analysis_provider, get_settings
from ..errors import (
    LakarraError,
    MetricsIncompleteError,
    MissingAccountHandleError,
    NotFoundError,
    TikTokFetchError,
)
from ..models.analytics import (
    AccountOverview,
    AccountSettingsRead,
    AnalysisResponse,
    AnalyzeAllResponse,
    CompetitorOverview,
    ContentAnalyticsPage,
    HistoricalAnalytics,
    MetricsReadiness,
    PerformanceMetrics,
    ReviewDecision,
    ReviewQueueItem,
    VideoCatalogItem,
    VideoInfo,
    VideoMetricsData,
    VideoMetricsRead,
    VideoUploadRead,
    normalize_tiktok_handle,
)
from ..models.content_analysis import (
    ContentAnalysis,
    MetricsPassOutput,
    VisualPassOutput,
)
from ..providers import (
    TikTokAccountData,
    TikTokVideoData,
    build_internal_content_provider,
    build_tiktok_provider,
)
from ..providers.tiktok_live import LiveTikTokProvider
from ..repositories.analytics_repository import AnalyticsRepository
from ..repositories.content_repository import ContentRepository
from .analysis_merge import merge_passes, project_video_analysis_summary
from .performance_analysis_builder import build_performance_analysis
from .prompts import load_prompt
from .storage_service import get_storage
from .video_metrics import (
    METRIC_FIELD_LABELS,
    OPTIONAL_METRIC_FIELDS,
    REQUIRED_METRIC_FIELDS,
    apply_metrics_to_performance,
    metrics_complete,
    metrics_from_row,
    missing_required,
    resolve_publish_metadata,
    video_display_label,
)
from .video_source import resolve_video_source

logger = logging.getLogger("lakarra.analytics_service")


def _safe_filename(name: str) -> str:
    safe = Path(name).name.strip()
    return safe if safe and safe not in {".", ".."} else "upload.mp4"


def _video_meta_from_payload(payload: dict) -> dict:
    perf = payload.get("performance_analysis")
    if isinstance(perf, dict):
        video = perf.get("video")
        if isinstance(video, dict):
            return video
    return {}


class AnalyticsService:
    def __init__(
        self,
        session: Session,
        analyst: ContentAnalystAgent | None = None,
    ) -> None:
        self.session = session
        self.repo = AnalyticsRepository(session)
        self.content_repo = ContentRepository(session)
        ctx = get_agent_context()
        self._analyst = analyst or ContentAnalystAgent(ctx)
        self._analyst.set_internal_provider(build_internal_content_provider(session))

    # --- Account handle ----------------------------------------------------
    def get_account_settings(self) -> AccountSettingsRead:
        row = self.repo.get_account_settings()
        if row and row.tiktok_handle:
            return AccountSettingsRead(
                tiktok_handle=row.tiktok_handle,
                configured=True,
                source="database",
            )
        env_handle = normalize_tiktok_handle(get_settings().tiktok_account_handle)
        if env_handle:
            return AccountSettingsRead(
                tiktok_handle=env_handle,
                configured=True,
                source="environment",
            )
        return AccountSettingsRead(configured=False, source="none")

    def set_account_handle(self, handle: str) -> AccountSettingsRead:
        normalized = normalize_tiktok_handle(handle)
        if not normalized:
            raise MissingAccountHandleError(
                "TikTok handle is required. Enter your @handle without the @ symbol."
            )
        self.repo.set_account_handle(normalized)
        self.session.commit()
        return AccountSettingsRead(
            tiktok_handle=normalized,
            configured=True,
            source="database",
        )

    def _resolve_handle(self) -> str | None:
        settings = self.get_account_settings()
        return settings.tiktok_handle if settings.configured else None

    def _require_handle(self) -> str:
        handle = self._resolve_handle()
        if not handle:
            raise MissingAccountHandleError(
                "No TikTok account connected. Set your @handle in Analytics settings "
                "or configure TIKTOK_ACCOUNT_HANDLE in the environment."
            )
        return handle

    def _bind_tiktok_provider(self) -> str:
        handle = self._require_handle()
        self._analyst.set_tiktok_provider(build_tiktok_provider(handle))
        return handle

    def _fetch_account(
        self, handle: str
    ) -> tuple[TikTokAccountData | None, str | None]:
        """Fetch TikTok account data; returns (account, optional live_data_error)."""

        account: TikTokAccountData | None = None
        live_data_error: str | None = None
        provider = build_tiktok_provider(handle)
        if isinstance(provider, LiveTikTokProvider):
            try:
                result = provider.fetch_account()
                account = result.account
                live_data_error = result.live_data_error
            except TikTokFetchError as exc:
                logger.warning("_fetch_account.tiktok_fetch_failed: %s", exc.message)
                live_data_error = exc.message
        else:
            try:
                account = provider.get_account()
            except TikTokFetchError as exc:
                logger.warning("_fetch_account.tiktok_fetch_failed: %s", exc.message)
                live_data_error = exc.message

        if account is None or not account.videos:
            fallback = self._account_from_stored_metrics(
                handle
            ) or self._account_from_posted_content(handle)
            if fallback is not None:
                if account is None:
                    account = fallback
                    live_data_error = (
                        live_data_error
                        or "Live TikTok video list unavailable; showing saved content."
                    )
                else:
                    account = TikTokAccountData(
                        handle=account.handle,
                        follower_count=account.follower_count,
                        videos=fallback.videos,
                    )
                    live_data_error = (
                        live_data_error
                        or "Could not load videos from TikTok; showing CMS posted content."
                    )

        return account, live_data_error

    def _performance_from_metrics_row(self, row) -> PerformanceMetrics:
        data = metrics_from_row(row)
        return PerformanceMetrics(
            views=int(data.get("views") or 0),
            reach=int(data.get("reach") or data.get("views") or 0),
            watch_time=float(data.get("watch_time") or 0),
            average_watch_duration=float(data.get("average_watch_duration") or 0),
            completion_rate=float(data.get("completion_rate") or 0),
            likes=int(data.get("likes") or 0),
            comments=int(data.get("comments") or 0),
            shares=int(data.get("shares") or 0),
            saves=int(data.get("saves") or 0),
            profile_visits=int(data.get("profile_visits") or 0),
            followers_gained=int(data.get("followers_gained") or 0),
            link_clicks=data.get("link_clicks"),
        )

    def _account_from_stored_metrics(self, handle: str) -> TikTokAccountData | None:
        rows = self.repo.list_video_metrics(tiktok_handle=handle)
        if not rows:
            return None

        analyses = self.repo.get_latest_analyses_map()
        videos: list[TikTokVideoData] = []
        for row in rows:
            payload = analyses[row.video_id].payload if row.video_id in analyses else {}
            video_meta = _video_meta_from_payload(payload)
            title = video_meta.get("title") or f"Video {row.video_id}"
            videos.append(
                TikTokVideoData(
                    video=VideoInfo(
                        video_id=row.video_id,
                        url=f"https://www.tiktok.com/@{handle}/video/{row.video_id}",
                        title=title,
                        caption=video_meta.get("caption", ""),
                        content_category=video_meta.get("content_category", "general"),
                    ),
                    performance=self._performance_from_metrics_row(row),
                    comments=[],
                )
            )
        return TikTokAccountData(handle=handle, follower_count=0, videos=videos)

    def _account_from_posted_content(self, handle: str) -> TikTokAccountData | None:
        items = build_internal_content_provider(self.session).list_posted_content()
        if not items:
            return None

        metrics_map = {
            m.video_id: m for m in self.repo.list_video_metrics(tiktok_handle=handle)
        }
        videos: list[TikTokVideoData] = []
        for content in items:
            row = metrics_map.get(content.id)
            performance = (
                self._performance_from_metrics_row(row)
                if row is not None
                else PerformanceMetrics()
            )
            videos.append(
                TikTokVideoData(
                    video=VideoInfo(
                        video_id=content.id,
                        title=content.title,
                        caption=content.caption,
                        hashtags=list(content.hashtags or []),
                        duration=content.duration,
                        content_category=content.category,
                    ),
                    performance=performance,
                    comments=[],
                )
            )
        return TikTokAccountData(handle=handle, follower_count=0, videos=videos)

    def _video_known(self, handle: str, video_id: str) -> bool:
        if self.repo.get_video_metrics(video_id) is not None:
            return True
        if build_internal_content_provider(self.session).get_content(video_id) is not None:
            return True
        provider = build_tiktok_provider(handle)
        try:
            return provider.get_video(video_id) is not None
        except TikTokFetchError:
            return False

    def _build_overview_from_account(
        self,
        handle: str,
        account: TikTokAccountData,
        *,
        live_data_error: str | None = None,
    ) -> AccountOverview:
        videos = account.videos
        if not videos:
            return AccountOverview(
                tiktok_handle=handle,
                account_configured=True,
                live_data_error=live_data_error,
            )

        total_views = sum(v.performance.views for v in videos)
        engagements = [
            (
                v.performance.likes
                + v.performance.comments
                + v.performance.shares
                + v.performance.saves
            )
            / max(v.performance.views, 1)
            for v in videos
        ]
        avg_engagement = sum(engagements) / len(engagements)

        sorted_by_views = sorted(videos, key=lambda v: v.performance.views, reverse=True)
        recent = [
            {
                "video_id": v.video.video_id,
                "title": video_display_label(title=v.video.title, caption=v.video.caption),
                "views": v.performance.views,
                "category": v.video.content_category,
                "publish_date": v.video.publish_date,
            }
            for v in videos[-5:]
        ]
        best = [
            {
                "video_id": v.video.video_id,
                "title": video_display_label(title=v.video.title, caption=v.video.caption),
                "views": v.performance.views,
                "engagement_rate": round(
                    (v.performance.likes + v.performance.comments) / max(v.performance.views, 1),
                    4,
                ),
            }
            for v in sorted_by_views[:3]
        ]
        worst = [
            {
                "video_id": v.video.video_id,
                "title": video_display_label(title=v.video.title, caption=v.video.caption),
                "views": v.performance.views,
            }
            for v in sorted_by_views[-3:]
        ]

        heatmap: dict[str, int] = {}
        for v in videos:
            day = v.video.publish_date[:10] if v.video.publish_date else "unknown"
            hour = v.video.publish_time[:2] if v.video.publish_time else "00"
            key = f"{day}|{hour}"
            heatmap[key] = heatmap.get(key, 0) + v.performance.views

        trends = [
            {
                "video_id": v.video.video_id,
                "title": video_display_label(title=v.video.title, caption=v.video.caption),
                "views": v.performance.views,
                "publish_date": v.video.publish_date,
            }
            for v in videos
        ]

        snapshots = self.repo.list_metrics_snapshots(limit=10)
        health_scores = [s for s in snapshots if s.metric == "account_health_score"]
        health = health_scores[0].value if health_scores else round(avg_engagement * 10, 2)

        return AccountOverview(
            tiktok_handle=handle,
            account_configured=True,
            live_data_error=live_data_error,
            account_health_score=min(health, 1.0) if health <= 1 else health / 10,
            total_videos=len(videos),
            total_views=total_views,
            avg_engagement_rate=round(avg_engagement, 4),
            recent_videos=recent,
            best_performers=best,
            worst_performers=worst,
            posting_heatmap=heatmap,
            performance_trends=trends,
            growth_trends=[{"followers": account.follower_count, "period": "current"}],
        )

    def _compute_metrics_readiness(
        self, handle: str, account: TikTokAccountData
    ) -> MetricsReadiness:
        metrics_map = {m.video_id: m for m in self.repo.list_video_metrics(tiktok_handle=handle)}
        sorted_videos = sorted(account.videos, key=lambda v: v.performance.views, reverse=True)
        priority_ids = {v.video.video_id for v in sorted_videos[:3] + sorted_videos[-3:]}

        incomplete: list[dict] = []
        complete = 0
        optional_recommended: list[str] = []
        for video in account.videos:
            vid = video.video.video_id
            row = metrics_map.get(vid)
            data = metrics_from_row(row)
            if metrics_complete(data):
                complete += 1
            else:
                incomplete.append(
                    {
                        "video_id": vid,
                        "title": video_display_label(
                            title=video.video.title, caption=video.video.caption
                        ),
                        "missing_required": missing_required(data),
                    }
                )
            if vid in priority_ids:
                optional_missing = [
                    f for f in OPTIONAL_METRIC_FIELDS if data.get(f) is None
                ]
                if optional_missing:
                    optional_recommended.append(vid)

        return MetricsReadiness(
            ready=complete == len(account.videos) and len(account.videos) > 0,
            total_videos=len(account.videos),
            complete_videos=complete,
            incomplete_videos=incomplete,
            required_fields=list(REQUIRED_METRIC_FIELDS),
            optional_fields=list(OPTIONAL_METRIC_FIELDS),
            optional_recommended_for=optional_recommended,
        )

    def _build_video_catalog(
        self, handle: str, account: TikTokAccountData
    ) -> list[VideoCatalogItem]:
        analyses = self.repo.get_latest_analyses_map()
        sorted_videos = sorted(account.videos, key=lambda v: v.performance.views, reverse=True)
        priority_ids = {v.video.video_id for v in sorted_videos[:3] + sorted_videos[-3:]}
        metrics_map = {m.video_id: m for m in self.repo.list_video_metrics(tiktok_handle=handle)}
        uploads_map = {u.video_id: u for u in self.repo.list_video_uploads(tiktok_handle=handle)}

        catalog: list[VideoCatalogItem] = []
        for video in account.videos:
            vid = video.video.video_id
            priority = "high" if vid in priority_ids else "normal"
            row = metrics_map.get(vid)
            upload = uploads_map.get(vid)
            latest = analyses.get(vid)
            payload = latest.payload if latest else {}
            publish_date, publish_time = resolve_publish_metadata(
                row,
                default_date=video.video.publish_date,
                default_time=video.video.publish_time,
            )
            analysis_summary = None
            if latest:
                try:
                    analysis_summary = project_video_analysis_summary(
                        ContentAnalysis.model_validate(payload)
                    )
                except Exception:  # noqa: BLE001
                    analysis_summary = None
            catalog.append(
                VideoCatalogItem(
                    video_id=vid,
                    title=video_display_label(
                        title=video.video.title, caption=video.video.caption
                    ),
                    url=video.video.url,
                    caption=video.video.caption,
                    publish_date=publish_date,
                    publish_time=publish_time,
                    duration=video.video.duration,
                    thumbnail=video.video.thumbnail,
                    is_analyzed=latest is not None,
                    analysis_version=latest.version if latest else None,
                    analysis_id=latest.id if latest else None,
                    analysis=analysis_summary,
                    has_video_upload=upload is not None,
                    upload_filename=upload.original_filename if upload else None,
                    metrics=self._metrics_read(vid, row, priority=priority),
                    metrics_priority=priority,
                )
            )
        return catalog

    def upload_video_file(
        self,
        video_id: str,
        *,
        data: bytes,
        mime_type: str,
        original_filename: str,
    ) -> VideoUploadRead:
        settings = get_settings()
        if len(data) > settings.max_upload_bytes:
            raise ValueError(
                f"File exceeds maximum size of {settings.max_upload_bytes // (1024 * 1024)} MB."
            )
        if mime_type not in settings.allowed_upload_mime_types:
            raise ValueError(f"Unsupported file type: {mime_type}")

        handle = self._require_handle()
        if not self._video_known(handle, video_id):
            raise NotFoundError(f"Video '{video_id}' not found.")

        existing = self.repo.get_video_upload(video_id)
        if existing is not None:
            try:
                get_storage().delete(existing.storage_key)
            except OSError:
                logger.warning("upload.delete_old_failed video_id=%s", video_id)

        storage_key = (
            f"analytics/{video_id}/{uuid4().hex}_{_safe_filename(original_filename)}"
        )
        get_storage().put_object(storage_key, data, content_type=mime_type)
        row = self.repo.upsert_video_upload(
            video_id=video_id,
            tiktok_handle=handle,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=len(data),
            original_filename=_safe_filename(original_filename),
        )
        self.session.commit()
        return VideoUploadRead(
            video_id=video_id,
            original_filename=row.original_filename,
            mime_type=row.mime_type,
            file_size=row.file_size,
            uploaded_at=row.updated_at,
        )

    def get_video_upload_row(self, video_id: str):
        return self.repo.get_video_upload(video_id)

    def delete_video_upload(self, video_id: str) -> None:
        row = self.repo.delete_video_upload(video_id)
        if row is None:
            raise NotFoundError(f"No upload found for video '{video_id}'.")
        try:
            get_storage().delete(row.storage_key)
        except OSError:
            logger.warning("upload.delete_storage_failed video_id=%s", video_id)
        self.session.commit()

    # --- Video metrics & catalog -------------------------------------------
    def _sync_public_metrics(self, handle: str, video: TikTokVideoData) -> None:
        existing = self.repo.get_video_metrics(video.video.video_id)
        if existing is not None:
            return
        perf = video.performance
        self.repo.upsert_video_metrics(
            video_id=video.video.video_id,
            tiktok_handle=handle,
            data={
                "views": perf.views,
                "likes": perf.likes,
                "comments": perf.comments,
                "shares": perf.shares,
                "saves": perf.saves,
                "reach": perf.reach or None,
                "watch_time": perf.watch_time or None,
                "average_watch_duration": perf.average_watch_duration or None,
                "completion_rate": perf.completion_rate or None,
                "profile_visits": perf.profile_visits or None,
                "followers_gained": perf.followers_gained or None,
                "link_clicks": perf.link_clicks,
            },
        )

    def _metrics_read(
        self, video_id: str, row, *, priority: str = "normal"
    ) -> VideoMetricsRead:
        data = metrics_from_row(row)
        missing = missing_required(data)
        return VideoMetricsRead(
            video_id=video_id,
            required_complete=metrics_complete(data),
            missing_required=missing,
            metrics_priority=priority,
            **{k: data.get(k) for k in REQUIRED_METRIC_FIELDS + OPTIONAL_METRIC_FIELDS},
            user_notes=row.user_notes if row else None,
            publish_date=row.publish_date if row else None,
            publish_time=row.publish_time if row else None,
        )

    def get_metrics_readiness(self) -> MetricsReadiness:
        handle = self._require_handle()
        account, _live_data_error = self._fetch_account(handle)
        if account is None:
            return MetricsReadiness(ready=False, total_videos=0, complete_videos=0)
        for video in account.videos:
            self._sync_public_metrics(handle, video)
        self.session.commit()
        return self._compute_metrics_readiness(handle, account)

    def _ensure_metrics_ready(self) -> None:
        readiness = self.get_metrics_readiness()
        if not readiness.ready:
            missing_titles = ", ".join(
                v["title"][:40] for v in readiness.incomplete_videos[:5]
            )
            raise MetricsIncompleteError(
                f"Complete required metrics (views, likes, comments, shares, saves) "
                f"for all videos before running account analytics. "
                f"Incomplete: {readiness.total_videos - readiness.complete_videos} video(s)"
                f"{f' — e.g. {missing_titles}' if missing_titles else ''}."
            )

    def get_content_page(self) -> ContentAnalyticsPage:
        settings = self.get_account_settings()
        labels = {
            "required_field_labels": {
                k: METRIC_FIELD_LABELS[k] for k in REQUIRED_METRIC_FIELDS
            },
            "optional_field_labels": {
                k: METRIC_FIELD_LABELS[k] for k in OPTIONAL_METRIC_FIELDS
            },
        }
        if not settings.configured or not settings.tiktok_handle:
            overview = AccountOverview(tiktok_handle=None, account_configured=False)
            return ContentAnalyticsPage(
                overview=overview,
                readiness=MetricsReadiness(ready=False, total_videos=0, complete_videos=0),
                videos=[],
                **labels,
            )

        handle = settings.tiktok_handle
        account, live_data_error = self._fetch_account(handle)
        if account is None:
            overview = AccountOverview(
                tiktok_handle=handle,
                account_configured=True,
                live_data_error=live_data_error,
            )
            return ContentAnalyticsPage(
                overview=overview,
                readiness=MetricsReadiness(ready=False, total_videos=0, complete_videos=0),
                videos=[],
                **labels,
            )

        for video in account.videos:
            self._sync_public_metrics(handle, video)
        self.session.commit()

        overview = self._build_overview_from_account(
            handle, account, live_data_error=live_data_error
        )
        readiness = self._compute_metrics_readiness(handle, account)
        catalog = self._build_video_catalog(handle, account)

        return ContentAnalyticsPage(
            overview=overview,
            readiness=readiness,
            videos=catalog,
            **labels,
        )

    def update_video_metrics(self, video_id: str, body: VideoMetricsData) -> VideoMetricsRead:
        handle = self._require_handle()
        if not self._video_known(handle, video_id):
            raise NotFoundError(f"Video '{video_id}' not found on connected account.")

        row = self.repo.upsert_video_metrics(
            video_id=video_id,
            tiktok_handle=handle,
            data=body.model_dump(exclude_unset=True),
        )
        self.session.commit()
        account, _ = self._fetch_account(handle)
        priority = "normal"
        if account is not None and account.videos:
            sorted_videos = sorted(
                account.videos, key=lambda v: v.performance.views, reverse=True
            )
            priority_ids = {
                v.video.video_id for v in sorted_videos[:3] + sorted_videos[-3:]
            }
            priority = "high" if video_id in priority_ids else "normal"
        return self._metrics_read(video_id, row, priority=priority)

    def _apply_user_metrics_to_video(self, video: TikTokVideoData) -> TikTokVideoData:
        row = self.repo.get_video_metrics(video.video.video_id)
        data = metrics_from_row(row)
        if not metrics_complete(data):
            raise MetricsIncompleteError(
                f"Complete required metrics for video '{video.video.title}' before analyzing."
            )
        perf_dict = video.performance.model_dump()
        merged = apply_metrics_to_performance(perf_dict, data)
        video.performance = type(video.performance)(**merged)
        if row is not None:
            if row.publish_date:
                video.video.publish_date = row.publish_date
            if row.publish_time:
                video.video.publish_time = row.publish_time
        return video

    # --- Analyze operations ------------------------------------------------
    def analyze_video(
        self,
        video_id: str,
        *,
        content_id: str | None = None,
        force: bool = False,
    ) -> AnalysisResponse:
        try:
            handle = self._bind_tiktok_provider()
            if not force:
                existing = self.repo.get_latest_analysis_for_video(video_id)
                if existing is not None:
                    return AnalysisResponse(
                        success=True,
                        skipped=True,
                        skip_reason="already_analyzed",
                        data=existing.payload,
                        analysis_id=existing.id,
                        version=existing.version,
                    )

            provider = build_tiktok_provider(handle)
            video_data = provider.get_video(video_id)
            if video_data is None:
                account, _ = self._fetch_account(handle)
                if account is not None:
                    for candidate in account.videos:
                        if candidate.video.video_id == video_id:
                            video_data = candidate
                            break
            if video_data is None:
                raise NotFoundError(f"Video '{video_id}' not found.")

            self._sync_public_metrics(handle, video_data)
            self.session.flush()
            video_data = self._apply_user_metrics_to_video(video_data)

            posted = self.content_repo.list_past_posts(exclude_id="", limit=10)
            historical = "\n".join(f"- {p.title} ({p.category})" for p in posted)
            metrics_result = self._analyst._analyze_video_data(  # noqa: SLF001
                video_data, historical_context=historical
            )
            metrics_pass = MetricsPassOutput(**metrics_result.payload)

            metrics_row = self.repo.get_video_metrics(video_id)
            performance_section = build_performance_analysis(
                video_data, metrics_row=metrics_row
            )

            source = resolve_video_source(
                self.session,
                video_id=video_id,
                tiktok_handle=handle,
            )
            visual_pass: VisualPassOutput | None = None
            visual_provider: str | None = None
            visual_model: str | None = None
            visual_prompt_version: str | None = None
            if source.bytes:
                visual_provider = effective_video_analysis_provider()
                visual_model = effective_video_analysis_model()
                visual_pass = self._analyst.analyze_video_visual(
                    video_bytes=source.bytes,
                    mime_type=source.mime_type,
                    video_data=video_data,
                    content=None,
                )
                visual_prompt_version = load_prompt("content_analyst_video_visual").version

            version = self.repo.next_content_analysis_version(video_id)
            merged = merge_passes(
                metrics_pass,
                visual_pass,
                performance_section,
                analysis_version=version,
                analysis_mode="full" if visual_pass else "metrics_only",
                video_source=source.source,
                linked_content_id=content_id,
                metrics_provider=metrics_result.provider,
                metrics_model=metrics_result.model,
                metrics_prompt_version=metrics_result.prompt_version,
                visual_provider=visual_provider,
                visual_model=visual_model,
                visual_prompt_version=visual_prompt_version,
            )
            merged_payload = merged.model_dump(mode="json")
            row = self.repo.save_content_analysis(
                video_id=video_id,
                content_id=None,
                version=version,
                agent=self._analyst.name,
                provider=metrics_result.provider,
                model=metrics_result.model,
                prompt_version=metrics_result.prompt_version,
                payload=merged_payload,
            )
            self._save_engagement_snapshots(merged_payload)
            self.session.commit()
            return AnalysisResponse(
                success=True,
                data=merged_payload,
                analysis_id=row.id,
                version=version,
            )
        except LakarraError as exc:
            logger.warning("analyze_video.failed type=%s", exc.error_type)
            return AnalysisResponse(
                success=False, error=exc.message, error_type=exc.error_type
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("analyze_video.unexpected")
            return AnalysisResponse(success=False, error=str(exc), error_type="error")

    def analyze_account(self) -> AnalysisResponse:
        try:
            self._ensure_metrics_ready()
            handle = self._bind_tiktok_provider()
            result = self._analyst.analyze_account()
            version = self.repo.next_pattern_version(handle)
            row = self.repo.save_pattern_analysis(
                subject_id=handle,
                version=version,
                agent=self._analyst.name,
                provider=result.provider,
                model=result.model,
                prompt_version=result.prompt_version,
                payload=result.payload,
            )
            self.session.commit()
            return AnalysisResponse(
                success=True,
                data=result.payload,
                analysis_id=row.id,
                version=version,
            )
        except LakarraError as exc:
            return AnalysisResponse(
                success=False, error=exc.message, error_type=exc.error_type
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("analyze_account.unexpected")
            return AnalysisResponse(success=False, error=str(exc), error_type="error")

    def analyze_competitor(self, handle: str) -> AnalysisResponse:
        try:
            self._bind_tiktok_provider()
            result = self._analyst.analyze_competitor(handle)
            version = self.repo.next_competitor_version(handle)
            row = self.repo.save_competitor_analysis(
                handle=handle,
                version=version,
                agent=self._analyst.name,
                provider=result.provider,
                model=result.model,
                prompt_version=result.prompt_version,
                payload=result.payload,
            )
            self.session.commit()
            return AnalysisResponse(
                success=True,
                data=result.payload,
                analysis_id=row.id,
                version=version,
            )
        except LakarraError as exc:
            return AnalysisResponse(
                success=False, error=exc.message, error_type=exc.error_type
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("analyze_competitor.unexpected")
            return AnalysisResponse(success=False, error=str(exc), error_type="error")

    def review_content(self, content_id: str) -> AnalysisResponse:
        try:
            content = self.content_repo.get(content_id)
            if content is None:
                raise NotFoundError("Content not found.")
            result = self._analyst.review_content(content)
            version = self.repo.next_review_version(content_id)
            row = self.repo.save_review_report(
                content_id=content_id,
                version=version,
                agent=self._analyst.name,
                provider=result.provider,
                model=result.model,
                prompt_version=result.prompt_version,
                payload=result.payload,
            )
            self.session.commit()
            return AnalysisResponse(
                success=True,
                data=result.payload,
                analysis_id=row.id,
                version=version,
            )
        except LakarraError as exc:
            return AnalysisResponse(
                success=False, error=exc.message, error_type=exc.error_type
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("review_content.unexpected")
            return AnalysisResponse(success=False, error=str(exc), error_type="error")

    def generate_trend_report(self, *, period: str = "30d") -> AnalysisResponse:
        try:
            self._ensure_metrics_ready()
            self._bind_tiktok_provider()
            result = self._analyst.generate_trend_report(period=period)
            version = self.repo.next_trend_version(period)
            row = self.repo.save_trend_report(
                period=period,
                version=version,
                agent=self._analyst.name,
                provider=result.provider,
                model=result.model,
                prompt_version=result.prompt_version,
                payload=result.payload,
            )
            health = result.payload.get("account_health_score", 0.0)
            self.repo.save_metrics_snapshot(
                metric="account_health_score",
                value=float(health),
                dimension=period,
            )
            self.session.commit()
            return AnalysisResponse(
                success=True,
                data=result.payload,
                analysis_id=row.id,
                version=version,
            )
        except LakarraError as exc:
            return AnalysisResponse(
                success=False, error=exc.message, error_type=exc.error_type
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("generate_trend_report.unexpected")
            return AnalysisResponse(success=False, error=str(exc), error_type="error")

    def analyze_all_videos(self) -> AnalyzeAllResponse:
        handle = self._require_handle()
        self._ensure_metrics_ready()
        provider = build_tiktok_provider(handle)
        analyzed_ids = self.repo.list_analyzed_video_ids()
        analyzed: list[AnalysisResponse] = []
        skipped: list[str] = []
        errors: list[dict] = []

        for video_data in provider.get_account().videos:
            vid = video_data.video.video_id
            if vid in analyzed_ids:
                skipped.append(vid)
                continue
            resp = self.analyze_video(vid)
            if resp.success and not resp.skipped:
                analyzed.append(resp)
            elif not resp.success:
                errors.append({"video_id": vid, "error": resp.error, "error_type": resp.error_type})

        return AnalyzeAllResponse(
            analyzed=analyzed,
            skipped_video_ids=skipped,
            errors=errors,
        )

    # --- Review decisions --------------------------------------------------
    def decide_review(
        self,
        report_id: str,
        *,
        decision: ReviewDecision,
        comment: str | None = None,
        decided_by: str = "user",
    ) -> AnalysisResponse:
        report = self.repo.get_review_report(report_id)
        if report is None:
            return AnalysisResponse(
                success=False, error="Review report not found.", error_type="not_found"
            )
        self.repo.update_review_decision(
            report, decision=decision.value, comment=comment, decided_by=decided_by
        )
        content = self.content_repo.get(report.content_id)
        if content is not None:
            status_map = {
                ReviewDecision.APPROVE: "approved",
                ReviewDecision.REJECT: "archived",
                ReviewDecision.REQUEST_REVISION: "draft",
            }
            new_status = status_map.get(decision)
            if new_status:
                self.content_repo.update_status(
                    content,
                    new_status=new_status,
                    changed_by=decided_by,
                    comment=comment or f"Review decision: {decision.value}",
                )
        self.session.commit()
        return AnalysisResponse(
            success=True,
            data={"decision": decision.value, "report_id": report_id},
        )

    # --- Read operations ---------------------------------------------------
    def get_overview(self) -> AccountOverview:
        settings = self.get_account_settings()
        if not settings.configured or not settings.tiktok_handle:
            return AccountOverview(
                tiktok_handle=None,
                account_configured=False,
            )

        account, live_data_error = self._fetch_account(settings.tiktok_handle)
        if account is None:
            return AccountOverview(
                tiktok_handle=settings.tiktok_handle,
                account_configured=True,
                live_data_error=live_data_error,
            )

        return self._build_overview_from_account(
            settings.tiktok_handle,
            account,
            live_data_error=live_data_error,
        )

    def get_competitor_overview(self) -> CompetitorOverview:
        from ..providers import build_competitor_provider

        provider = build_competitor_provider()
        handles = self.repo.list_competitor_handles(limit=20)
        if not handles and get_settings().tiktok_provider == "mock":
            handles = provider.list_known_competitors()

        competitors = []
        for handle in handles:
            try:
                account = provider.get_account(handle)
                competitors.append(
                    {
                        "handle": account.handle,
                        "follower_count": account.follower_count,
                        "average_views": account.average_views,
                        "engagement_rate": account.engagement_rate,
                        "posting_frequency": account.posting_frequency,
                    }
                )
            except LakarraError:
                logger.warning("competitor.fetch.failed handle=%s", handle)
        analyses = self.repo.list_competitor_analyses(limit=10)
        from ..models.analytics import CompetitorAnalysisRead

        return CompetitorOverview(
            competitors=competitors,
            latest_analyses=[
                CompetitorAnalysisRead(
                    id=a.id,
                    version=a.version,
                    subject_id=a.handle,
                    agent=a.agent,
                    provider=a.provider,
                    model=a.model,
                    prompt_version=a.prompt_version,
                    payload=a.payload,
                    created_at=a.created_at,
                    handle=a.handle,
                )
                for a in analyses
            ],
        )

    def get_review_queue(self) -> list[ReviewQueueItem]:
        internal = build_internal_content_provider(self.session)
        items = internal.list_review_queue()
        result = []
        for content in items:
            latest = self.repo.latest_review_for_content(content.id)
            from ..models.analytics import ReviewReportRead

            review_read = None
            if latest:
                review_read = ReviewReportRead(
                    id=latest.id,
                    version=latest.version,
                    subject_id=latest.content_id,
                    agent=latest.agent,
                    provider=latest.provider,
                    model=latest.model,
                    prompt_version=latest.prompt_version,
                    payload=latest.payload,
                    created_at=latest.created_at,
                    content_id=latest.content_id,
                    decision=latest.decision,
                    decision_comment=latest.decision_comment,
                    decided_by=latest.decided_by,
                    decided_at=latest.decided_at,
                )
            result.append(
                ReviewQueueItem(
                    content_id=content.id,
                    title=content.title,
                    category=content.category,
                    status=content.status,
                    confidence_score=content.confidence_score,
                    latest_review=review_read,
                    created_at=content.created_at,
                    updated_at=content.updated_at,
                )
            )
        return result

    def get_historical(self) -> HistoricalAnalytics:
        from ..models.analytics import (
            CompetitorAnalysisRead,
            ContentAnalysisRead,
            MetricsSnapshotRead,
            PatternAnalysisRead,
            ReviewReportRead,
            TrendReportRead,
        )

        return HistoricalAnalytics(
            content_analyses=[
                ContentAnalysisRead(
                    id=a.id,
                    version=a.version,
                    subject_id=a.video_id,
                    agent=a.agent,
                    provider=a.provider,
                    model=a.model,
                    prompt_version=a.prompt_version,
                    payload=a.payload,
                    created_at=a.created_at,
                    video_id=a.video_id,
                )
                for a in self.repo.list_content_analyses(limit=50)
            ],
            competitor_analyses=[
                CompetitorAnalysisRead(
                    id=a.id,
                    version=a.version,
                    subject_id=a.handle,
                    agent=a.agent,
                    provider=a.provider,
                    model=a.model,
                    prompt_version=a.prompt_version,
                    payload=a.payload,
                    created_at=a.created_at,
                    handle=a.handle,
                )
                for a in self.repo.list_competitor_analyses(limit=50)
            ],
            trend_reports=[
                TrendReportRead(
                    id=a.id,
                    version=a.version,
                    subject_id=a.period,
                    agent=a.agent,
                    provider=a.provider,
                    model=a.model,
                    prompt_version=a.prompt_version,
                    payload=a.payload,
                    created_at=a.created_at,
                    period=a.period,
                )
                for a in self.repo.list_trend_reports(limit=20)
            ],
            review_reports=[
                ReviewReportRead(
                    id=a.id,
                    version=a.version,
                    subject_id=a.content_id,
                    agent=a.agent,
                    provider=a.provider,
                    model=a.model,
                    prompt_version=a.prompt_version,
                    payload=a.payload,
                    created_at=a.created_at,
                    content_id=a.content_id,
                    decision=a.decision,
                    decision_comment=a.decision_comment,
                    decided_by=a.decided_by,
                    decided_at=a.decided_at,
                )
                for a in self.repo.list_review_reports(limit=50)
            ],
            pattern_analyses=[
                PatternAnalysisRead(
                    id=a.id,
                    version=a.version,
                    subject_id=a.subject_id,
                    agent=a.agent,
                    provider=a.provider,
                    model=a.model,
                    prompt_version=a.prompt_version,
                    payload=a.payload,
                    created_at=a.created_at,
                )
                for a in self.repo.list_pattern_analyses(limit=20)
            ],
            metrics_snapshots=[
                MetricsSnapshotRead.model_validate(s)
                for s in self.repo.list_metrics_snapshots(limit=100)
            ],
        )

    def _save_engagement_snapshots(self, payload: dict) -> None:
        perf = payload.get("performance_analysis", {})
        if not isinstance(perf, dict):
            return
        engagement = perf.get("engagement", {})
        video = perf.get("video", {})
        vid = video.get("video_id", "unknown") if isinstance(video, dict) else "unknown"
        if not isinstance(engagement, dict):
            return
        for metric, value in engagement.items():
            if isinstance(value, (int, float)):
                self.repo.save_metrics_snapshot(
                    metric=metric,
                    value=float(value),
                    dimension=vid,
                )
