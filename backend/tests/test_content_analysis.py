"""Tests for unified VIDEO + IMAGE content analysis."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.agents.content_analyst import ContentAnalystAgent
from app.config import effective_visual_analysis_provider, get_settings
from app.main import app
from app.models.content_analysis import ContentType
from app.providers import MockTikTokProvider, build_internal_content_provider
from app.repositories.analytics_repository import AnalyticsRepository
from app.services.analytics_service import AnalyticsService
from fastapi.testclient import TestClient


@pytest.fixture
def analyst(db_session: Session):
    from app.agents import get_agent_context

    agent = ContentAnalystAgent(
        get_agent_context(),
        tiktok=MockTikTokProvider("lakarra"),
    )
    agent.set_internal_provider(build_internal_content_provider(db_session))
    return agent


@pytest.fixture
def analytics_service(db_session: Session, analyst: ContentAnalystAgent):
    return AnalyticsService(db_session, analyst=analyst)


class TestContentAnalysisFlows:
    def test_metrics_dimensions_accept_llm_scalar_shorthand(self):
        from app.models.content_analysis import VideoContentAnalysisSection

        section = VideoContentAnalysisSection(
            type="VIDEO",
            hook="The hook loses curiosity too early.",
            story_script={"score": 0.6, "explanation": "Story is inferred from completion."},
            voiceover={"score": 5, "confidence": "medium", "explanation": "Limited evidence."},
            pacing="Pacing appears inconsistent.",
            scenes=[
                {
                    "start": 0,
                    "end": 3,
                    "scene": {"description": "Opening hook"},
                }
            ],
        )

        assert section.hook.score == 5
        assert section.story_script.score == 6
        assert section.voiceover.score == 5
        assert section.pacing.explanation == "Pacing appears inconsistent."
        assert section.scenes[0].start_timestamp == "0"
        assert section.scenes[0].end_timestamp == "3"
        assert section.scenes[0].purpose == "Opening hook"

    def test_video_metrics_only(self, analytics_service: AnalyticsService):
        resp = analytics_service.analyze_content("lk-001", force=True)
        assert resp.success is True
        assert resp.data["metadata"]["content_type"] == "VIDEO"
        assert resp.data["metadata"]["analysis_mode"] == "metrics_only"

    def test_video_full_with_upload(self, analytics_service: AnalyticsService, db_session: Session):
        repo = AnalyticsRepository(db_session)
        repo.upsert_video_upload(
            video_id="lk-004",
            tiktok_handle="lakarra",
            storage_key="analytics/lk-004/full.mp4",
            mime_type="video/mp4",
            file_size=20,
            original_filename="clip.mp4",
        )
        db_session.commit()

        mock_storage = MagicMock()
        mock_storage.read_object.return_value = b"uploaded-video-bytes"
        with patch("app.services.media_resolver.get_storage", return_value=mock_storage):
            resp = analytics_service.analyze_content("lk-004", force=True)

        assert resp.success is True
        assert resp.data["metadata"]["analysis_mode"] == "full"
        assert resp.data["content_analysis"]["type"] == "VIDEO"

    def test_image_metrics_only(self, analytics_service: AnalyticsService):
        resp = analytics_service.analyze_content(
            "lk-002",
            content_type=ContentType.IMAGE,
            force=True,
        )
        assert resp.success is True
        assert resp.data["metadata"]["content_type"] == "IMAGE"
        assert resp.data["metadata"]["analysis_mode"] == "metrics_only"
        assert resp.data["content_analysis"]["type"] == "IMAGE"

    def test_image_full_with_upload(self, analytics_service: AnalyticsService, db_session: Session):
        repo = AnalyticsRepository(db_session)
        repo.upsert_video_upload(
            video_id="lk-003",
            tiktok_handle="lakarra",
            storage_key="analytics/lk-003/cover.jpg",
            mime_type="image/jpeg",
            file_size=12,
            original_filename="cover.jpg",
        )
        db_session.commit()

        mock_storage = MagicMock()
        mock_storage.read_object.return_value = b"image-bytes"
        with patch("app.services.media_resolver.get_storage", return_value=mock_storage):
            resp = analytics_service.analyze_content(
                "lk-003",
                content_type=ContentType.IMAGE,
                force=True,
            )

        assert resp.success is True
        assert resp.data["metadata"]["analysis_mode"] == "full"
        assert resp.data["content_analysis"]["type"] == "IMAGE"
        assert resp.data["content_analysis"]["composition"]["score"] >= 1

    def test_provider_selection_mock_default(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("VISUAL_ANALYSIS_PROVIDER", "mock")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        get_settings.cache_clear()
        assert effective_visual_analysis_provider() == "mock"

    def test_content_analyze_endpoint(self, analytics_service: AnalyticsService):
        _ = analytics_service
        client = TestClient(app)
        resp = client.post("/api/analytics/content/lk-001/analyze?force=true")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["metadata"]["content_type"] == "VIDEO"

    def test_legacy_video_endpoint_delegates(self, analytics_service: AnalyticsService):
        _ = analytics_service
        client = TestClient(app)
        resp = client.post("/api/analytics/videos/lk-002/analyze?force=true")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
