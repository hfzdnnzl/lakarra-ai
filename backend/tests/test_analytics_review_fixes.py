"""Regression tests for PR review fixes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.agents import get_agent_context
from app.agents.content_analyst import ContentAnalystAgent
from app.agents.content_analyst.input_builder import build_content_analysis_input
from app.config import effective_visual_analysis_provider, get_settings
from app.errors import TikTokFetchError
from app.models.db import Content
from app.providers import MockTikTokProvider, TikTokAccountData, build_internal_content_provider
from app.repositories.analytics_repository import AnalyticsRepository
from app.services.analytics_service import AnalyticsService, _video_meta_from_payload


@pytest.fixture
def analyst(db_session: Session):
    agent = ContentAnalystAgent(
        get_agent_context(),
        tiktok=MockTikTokProvider("lakarra"),
    )
    agent.set_internal_provider(build_internal_content_provider(db_session))
    return agent


@pytest.fixture
def analytics_service(db_session: Session, analyst: ContentAnalystAgent):
    return AnalyticsService(db_session, analyst=analyst)


class TestReviewFixes:
    def test_video_meta_from_payload_reads_post(self):
        meta = _video_meta_from_payload(
            {
                "performance_analysis": {
                    "post": {"title": "My post", "caption": "Hello"},
                }
            }
        )
        assert meta["title"] == "My post"

    def test_video_meta_from_payload_legacy_video_key(self):
        meta = _video_meta_from_payload(
            {
                "performance_analysis": {
                    "video": {"title": "Legacy", "caption": "Old"},
                }
            }
        )
        assert meta["title"] == "Legacy"

    def test_input_builder_uses_content_repository_get(self, db_session: Session):
        content = Content(
            id=uuid4().hex,
            title="Linked plan",
            category="pov",
            business_goal="awareness",
            target_audience="couples",
            product="invites",
            hook="Hook",
            duration=20,
            caption="Caption",
            hashtags=[],
            cta="CTA",
            posting_time="18:00",
            confidence_score=0.8,
            status="posted",
        )
        db_session.add(content)
        db_session.commit()

        post_data = MockTikTokProvider("lakarra").get_video("lk-001")
        assert post_data is not None
        built = build_content_analysis_input(
            db_session,
            post_data=post_data,
            post_id="lk-001",
            linked_content_id=content.id,
        )
        assert built.linked_content_id == content.id

    def test_analyze_content_resolves_cms_link_by_tiktok_video_id(
        self, analytics_service: AnalyticsService, db_session: Session
    ):
        content = Content(
            id=uuid4().hex,
            title="Linked via TikTok ID",
            category="pov",
            business_goal="awareness",
            target_audience="couples",
            product="invites",
            hook="Hook",
            duration=20,
            caption="Caption",
            hashtags=[],
            cta="CTA",
            posting_time="18:00",
            confidence_score=0.8,
            status="posted",
            tiktok_video_id="lk-001",
        )
        db_session.add(content)
        db_session.commit()

        resp = analytics_service.analyze_content("lk-001", force=True)
        assert resp.success is True
        assert resp.data["metadata"].get("linked_content_id") == content.id

    def test_analyze_all_uses_fetch_account_fallback(
        self, analytics_service: AnalyticsService, monkeypatch: pytest.MonkeyPatch
    ):
        account = TikTokAccountData(handle="lakarra", follower_count=0, videos=[])

        def fake_fetch(_handle: str):
            post = MockTikTokProvider("lakarra").get_video("lk-002")
            assert post is not None
            return TikTokAccountData(handle="lakarra", follower_count=0, videos=[post]), "offline"

        monkeypatch.setattr(analytics_service, "_fetch_account", fake_fetch)
        monkeypatch.setattr(analytics_service, "_ensure_metrics_ready", lambda: None)

        result = analytics_service.analyze_all_videos()
        assert result.errors == []
        assert any(r.success for r in result.analyzed) or "lk-002" in result.skipped_video_ids

    def test_legacy_video_analysis_env_alias(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("VIDEO_ANALYSIS_PROVIDER", "mock")
        monkeypatch.delenv("VISUAL_ANALYSIS_PROVIDER", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        get_settings.cache_clear()
        assert effective_visual_analysis_provider() == "mock"

    def test_carousel_download_fails_on_partial_slide(self, monkeypatch: pytest.MonkeyPatch):
        from app.providers import tiktok_live

        class FakeResponse:
            def __init__(self, status_code: int, content: bytes = b"img"):
                self.status_code = status_code
                self.content = content
                self.headers = {"content-type": "image/jpeg"}

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def post(self, *args, **kwargs):
                return {"images": ["http://a/1.jpg", "http://a/2.jpg"]}

            def get(self, url, timeout=0):
                if url.endswith("2.jpg"):
                    return FakeResponse(404)
                return FakeResponse(200)

        monkeypatch.setattr(tiktok_live, "_client", lambda: FakeClient())
        monkeypatch.setattr(tiktok_live, "_post_json", lambda client, path, data=None: {"images": ["http://a/1.jpg", "http://a/2.jpg"]})

        with pytest.raises(TikTokFetchError, match="slide 2"):
            tiktok_live.download_tiktok_carousel("brand", "post123")

    def test_carousel_manifest_upload_mime_allowed(self, analytics_service: AnalyticsService):
        settings = get_settings()
        assert "application/vnd.lakarra.carousel+json" in settings.allowed_upload_mime_types
