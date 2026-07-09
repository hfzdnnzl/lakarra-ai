"""Tests for Content Analyst Phase 3 analytics."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agents import get_agent_context
from app.agents.content_analyst import ContentAnalystAgent
from app.main import app
from app.models.analytics import ContentRecommendations
from app.providers import MockTikTokProvider, build_internal_content_provider
from app.repositories.analytics_repository import AnalyticsRepository
from app.services.analytics_service import AnalyticsService


@pytest.fixture
def analyst(db_session: Session):
    ctx = get_agent_context()
    agent = ContentAnalystAgent(
        ctx,
        tiktok=MockTikTokProvider("lakarra"),
    )
    agent.set_internal_provider(build_internal_content_provider(db_session))
    return agent


@pytest.fixture
def analytics_service(db_session: Session, analyst: ContentAnalystAgent):
    return AnalyticsService(db_session, analyst=analyst)


class TestContentAnalystAgent:
    def test_content_recommendations_coerces_string_lists(self):
        rec = ContentRecommendations(
            posting_schedule="Post on Friday evenings and Saturday mornings.",
            strategy_gaps="No trend-jacking content this week.",
        )
        assert rec.posting_schedule == ["Post on Friday evenings and Saturday mornings."]
        assert rec.strategy_gaps == ["No trend-jacking content this week."]

    def test_analyze_video(self, analyst: ContentAnalystAgent):
        result = analyst.analyze_video("lk-001")
        assert result.payload["video"]["video_id"] == "lk-001"
        assert "engagement" in result.payload
        assert "quality_scores" in result.payload

    def test_analyze_account(self, analyst: ContentAnalystAgent):
        result = analyst.analyze_account()
        assert "best_performing_categories" in result.payload
        assert result.provider == "mock"

    def test_analyze_competitor(self, analyst: ContentAnalystAgent):
        result = analyst.analyze_competitor("paperlesspost")
        assert result.payload["account"]["handle"] == "paperlesspost"
        assert "strengths" in result.payload
        assert "opportunities" in result.payload

    def test_generate_trend_report(self, analyst: ContentAnalystAgent):
        result = analyst.generate_trend_report(period="30d")
        assert result.payload["period"] == "30d"
        assert "patterns" in result.payload
        assert "recommendations" in result.payload

    def test_analyze_all_videos(self, analyst: ContentAnalystAgent):
        results = analyst.analyze_all_videos()
        assert len(results) == 5


class TestAnalyticsService:
    def test_account_settings_round_trip(self, analytics_service: AnalyticsService):
        settings = analytics_service.get_account_settings()
        assert settings.configured is True  # from TIKTOK_ACCOUNT_HANDLE in conftest

        updated = analytics_service.set_account_handle("mybrand")
        assert updated.tiktok_handle == "mybrand"
        assert updated.configured is True
        assert updated.source == "database"

    def test_analyze_without_handle_fails(self, db_session: Session):
        import os

        from app.config import get_settings

        old = os.environ.pop("TIKTOK_ACCOUNT_HANDLE", None)
        get_settings.cache_clear()
        try:
            service = AnalyticsService(db_session)
            resp = service.analyze_account()
            assert resp.success is False
            assert resp.error_type == "missing_account_handle"
        finally:
            if old is not None:
                os.environ["TIKTOK_ACCOUNT_HANDLE"] = old
            get_settings.cache_clear()

    def test_analyze_video_persists(self, analytics_service: AnalyticsService, db_session: Session):
        resp = analytics_service.analyze_video("lk-001")
        assert resp.success is True
        assert resp.analysis_id is not None
        assert resp.version == 1

        repo = AnalyticsRepository(db_session)
        rows = repo.list_content_analyses(video_id="lk-001")
        assert len(rows) == 1

    def test_versioning_never_overwrites(self, analytics_service: AnalyticsService):
        first = analytics_service.analyze_video("lk-002")
        second = analytics_service.analyze_video("lk-002", force=True)
        assert first.success and second.success
        assert first.version == 1
        assert second.version == 2
        assert first.analysis_id != second.analysis_id
        assert not first.skipped
        assert not second.skipped

    def test_analyze_skips_already_analyzed(self, analytics_service: AnalyticsService):
        first = analytics_service.analyze_video("lk-003")
        second = analytics_service.analyze_video("lk-003")
        assert first.success and not first.skipped
        assert second.success and second.skipped
        assert second.skip_reason == "already_analyzed"

    def test_analyze_all_skips_analyzed(self, analytics_service: AnalyticsService):
        analytics_service.analyze_video("lk-001")
        result = analytics_service.analyze_all_videos()
        assert "lk-001" in result.skipped_video_ids
        assert len(result.analyzed) >= 1

    def test_analyze_competitor_persists(self, analytics_service: AnalyticsService):
        resp = analytics_service.analyze_competitor("greenvelope")
        assert resp.success is True
        assert resp.version == 1

    def test_generate_trend_report_persists(self, analytics_service: AnalyticsService):
        resp = analytics_service.generate_trend_report(period="30d")
        assert resp.success is True
        assert resp.data is not None

    def test_get_overview(self, analytics_service: AnalyticsService):
        overview = analytics_service.get_overview()
        assert overview.total_videos == 5
        assert overview.total_views > 0

    def test_get_overview_degraded_on_tiktok_fetch_error(
        self, analytics_service: AnalyticsService, monkeypatch: pytest.MonkeyPatch
    ):
        from app.errors import TikTokFetchError
        from app.providers import TikTokProvider

        class FailingProvider(TikTokProvider):
            def get_account(self):
                raise TikTokFetchError("TikTok data request failed (HTTP 531).")

            def get_video(self, video_id: str):
                return None

        monkeypatch.setattr(
            "app.services.analytics_service.build_tiktok_provider",
            lambda _handle: FailingProvider(),
        )
        overview = analytics_service.get_overview()
        assert overview.account_configured is True
        assert overview.live_data_error is not None
        assert overview.total_videos == 0

    def test_get_content_page_shows_videos_with_live_data_error(
        self, analytics_service: AnalyticsService, monkeypatch: pytest.MonkeyPatch
    ):
        from app.models.analytics import PerformanceMetrics, VideoInfo
        from app.providers import TikTokAccountData, TikTokVideoData

        sample_video = TikTokVideoData(
            video=VideoInfo(
                video_id="lk-stale",
                url="https://tiktok.com/@lakarra/video/lk-stale",
                title="Stale video",
                caption="Stale",
                hashtags=[],
                publish_date="2026-01-01",
                publish_time="10:00",
                duration=20,
                thumbnail="",
                content_category="general",
            ),
            performance=PerformanceMetrics(
                views=100,
                reach=100,
                watch_time=50.0,
                average_watch_duration=20.0,
                completion_rate=0.0,
                retention_curve=[],
                likes=10,
                comments=2,
                shares=1,
                saves=3,
                profile_visits=0,
                followers_gained=0,
                link_clicks=None,
            ),
            comments=[],
        )
        sample_account = TikTokAccountData(
            handle="lakarra", follower_count=1000, videos=[sample_video]
        )

        monkeypatch.setattr(
            analytics_service,
            "_fetch_account",
            lambda _handle: (
                sample_account,
                "Could not refresh live TikTok data: rate limited.",
            ),
        )

        page = analytics_service.get_content_page()
        assert page.overview.live_data_error is not None
        assert len(page.videos) == 1
        assert page.videos[0].video_id == "lk-stale"
        assert page.readiness.total_videos == 1

    def test_get_content_page_falls_back_to_posted_cms_content(
        self,
        analytics_service: AnalyticsService,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ):
        from uuid import uuid4

        from app.models.db import Content

        content = Content(
            id=uuid4().hex,
            title="Posted wedding invite",
            category="aesthetic",
            business_goal="awareness",
            target_audience="couples",
            product="digital invites",
            hook="POV your invite arrives",
            duration=25,
            caption="Beautiful digital invites",
            hashtags=["wedding"],
            cta="Link in bio",
            posting_time="18:00",
            confidence_score=0.9,
            status="posted",
        )
        db_session.add(content)
        db_session.commit()

        monkeypatch.setattr(
            analytics_service,
            "_fetch_account",
            lambda handle: (
                analytics_service._account_from_posted_content(handle),
                "TikTok data request failed (HTTP 531).",
            ),
        )

        page = analytics_service.get_content_page()
        assert page.overview.live_data_error is not None
        assert len(page.videos) == 1
        assert page.videos[0].title == "Beautiful digital invites"

    def test_get_historical(self, analytics_service: AnalyticsService):
        analytics_service.analyze_account()
        historical = analytics_service.get_historical()
        assert len(historical.pattern_analyses) >= 1


class TestAnalyticsAPI:
  @pytest.fixture
  def client(self):
      return TestClient(app)

  def test_account_settings_endpoint(self, client: TestClient):
      resp = client.get("/api/analytics/account/settings")
      assert resp.status_code == 200
      data = resp.json()
      assert data["configured"] is True
      assert data["tiktok_handle"] == "lakarra"

  def test_update_account_settings_endpoint(self, client: TestClient):
      resp = client.put(
          "/api/analytics/account/settings",
          json={"tiktok_handle": "@myweddingbrand"},
      )
      assert resp.status_code == 200
      assert resp.json()["tiktok_handle"] == "myweddingbrand"

  def test_overview_endpoint(self, client: TestClient):
      resp = client.get("/api/analytics/overview")
      assert resp.status_code == 200
      data = resp.json()
      assert "total_videos" in data
      assert data["total_videos"] == 5

  def test_analyze_account_endpoint(self, client: TestClient):
      resp = client.post("/api/analytics/account/analyze")
      assert resp.status_code == 200
      data = resp.json()
      assert data["success"] is True

  def test_analyze_video_endpoint(self, client: TestClient):
      resp = client.post(
          "/api/analytics/videos/analyze",
          json={"video_id": "lk-001"},
      )
      assert resp.status_code == 200
      assert resp.json()["success"] is True

  def test_analyze_competitor_endpoint(self, client: TestClient):
      resp = client.post(
          "/api/analytics/competitors/analyze",
          json={"handle": "paperlesspost"},
      )
      assert resp.status_code == 200
      assert resp.json()["success"] is True

  def test_content_page_endpoint(self, client: TestClient):
      resp = client.get("/api/analytics/content")
      assert resp.status_code == 200
      data = resp.json()
      assert "videos" in data
      assert "readiness" in data
      assert len(data["videos"]) == 5

  def test_update_video_metrics_endpoint(self, client: TestClient):
      resp = client.put(
          "/api/analytics/videos/lk-001/metrics",
          json={"views": 50000, "likes": 1000, "comments": 50, "shares": 20, "saves": 80},
      )
      assert resp.status_code == 200
      assert resp.json()["required_complete"] is True

  def test_analyze_all_skips_endpoint(self, client: TestClient):
      client.post("/api/analytics/videos/lk-001/analyze")
      resp = client.post("/api/analytics/videos/analyze-all")
      assert resp.status_code == 200
      data = resp.json()
      assert "lk-001" in data["skipped_video_ids"]
      resp = client.get("/api/analytics/historical")
      assert resp.status_code == 200
      data = resp.json()
      assert "content_analyses" in data
      assert "trend_reports" in data

  def test_review_queue_endpoint(self, client: TestClient):
      resp = client.get("/api/analytics/review-queue")
      assert resp.status_code == 200
      assert isinstance(resp.json(), list)
