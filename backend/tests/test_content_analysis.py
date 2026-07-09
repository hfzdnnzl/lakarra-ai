"""Tests for unified VIDEO + IMAGE content analysis architecture."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.agents import get_agent_context
from app.agents.content_analyst import ContentAnalystAgent
from app.agents.content_analyst.input_builder import build_analysis_input, parse_content_type
from app.agents.content_analyst.merge import merge_passes
from app.errors import InvalidContentTypeError
from app.models.analytics import VideoMetricsData
from app.models.content_analysis import (
    AnalysisMode,
    ContentAnalysisInput,
    ContentType,
    MetricsPassOutput,
)
from app.providers import MockTikTokProvider, TikTokVideoData, build_internal_content_provider
from app.services.analytics_mock import build_metrics_pass_response
from app.services.analytics_service import AnalyticsService
from app.services.content_visual_analysis import (
    ContentVisualAnalysisService,
    MockVisualProvider,
    build_visual_provider,
)


@pytest.fixture
def analyst(db_session: Session):
    ctx = get_agent_context()
    agent = ContentAnalystAgent(ctx, tiktok=MockTikTokProvider("lakarra"))
    agent.set_internal_provider(build_internal_content_provider(db_session))
    return agent


@pytest.fixture
def analytics_service(db_session: Session, analyst: ContentAnalystAgent):
    return AnalyticsService(db_session, analyst=analyst)


def _metrics_output(data: TikTokVideoData) -> MetricsPassOutput:
    import json

    from app.models.content_analysis import MetricsPassOutput

    raw = json.loads(build_metrics_pass_response(data))
    raw.pop("provider", None)
    raw.pop("model", None)
    raw.pop("prompt_version", None)
    return MetricsPassOutput(**raw, provider="mock", model="mock-model", prompt_version="test")


class TestContentTypeHandling:
    def test_parse_video_type(self, analyst: ContentAnalystAgent):
        data = analyst._tiktok_or_raise().get_video("lk-001")
        assert data is not None
        assert parse_content_type(data.video) == ContentType.VIDEO

    def test_parse_image_type(self, analyst: ContentAnalystAgent):
        data = analyst._tiktok_or_raise().get_video("lk-img-001")
        assert data is not None
        assert parse_content_type(data.video) == ContentType.IMAGE

    def test_invalid_content_type_raises(self):
        from app.models.analytics import VideoInfo

        with pytest.raises(InvalidContentTypeError):
            parse_content_type(VideoInfo(video_id="x", content_type="CAROUSEL"))


class TestVideoAnalysisFlow:
    def test_video_metrics_visual_merge(self, analyst: ContentAnalystAgent):
        data = analyst._tiktok_or_raise().get_video("lk-001")
        assert data is not None
        analysis_input = build_analysis_input(data)
        metrics = _metrics_output(data)
        visual = MockVisualProvider().analyze(
            content_type=ContentType.VIDEO,
            media_bytes=b"mock-video",
            mime_type="video/mp4",
            context_json="{}",
        )
        merged = merge_passes(
            analysis_input=analysis_input,
            metrics=metrics,
            visual=visual,
            analysis_mode=AnalysisMode.FULL,
        )
        assert merged.metadata.content_type == ContentType.VIDEO
        assert merged.metadata.analysis_mode == AnalysisMode.FULL
        assert merged.content_analysis is not None
        assert "hook" in merged.content_analysis.model_dump()
        assert merged.executive_summary

    def test_analyze_video_end_to_end(self, analytics_service: AnalyticsService):
        analytics_service.update_video_metrics(
            "lk-001",
            VideoMetricsData(
                views=50_000,
                likes=3_000,
                comments=100,
                shares=50,
                saves=200,
            ),
        )
        resp = analytics_service.analyze_content("lk-001")
        assert resp.success is True
        assert resp.data is not None
        assert resp.data["metadata"]["content_type"] == "VIDEO"
        assert resp.data["metadata"]["analysis_mode"] == "full"
        assert "content_analysis" in resp.data


class TestImageAnalysisFlow:
    def test_image_visual_merge(self, analyst: ContentAnalystAgent):
        data = analyst._tiktok_or_raise().get_video("lk-img-001")
        assert data is not None
        analysis_input = build_analysis_input(data)
        metrics = _metrics_output(data)
        visual = MockVisualProvider().analyze(
            content_type=ContentType.IMAGE,
            media_bytes=b"mock-image",
            mime_type="image/jpeg",
            context_json="{}",
        )
        merged = merge_passes(
            analysis_input=analysis_input,
            metrics=metrics,
            visual=visual,
            analysis_mode=AnalysisMode.FULL,
        )
        assert merged.metadata.content_type == ContentType.IMAGE
        payload = merged.content_analysis.model_dump() if merged.content_analysis else {}
        assert "composition" in payload

    def test_analyze_image_end_to_end(self, analytics_service: AnalyticsService):
        analytics_service.update_video_metrics(
            "lk-img-001",
            VideoMetricsData(
                views=90_000,
                likes=7_000,
                comments=400,
                shares=900,
                saves=2_500,
            ),
        )
        resp = analytics_service.analyze_content("lk-img-001")
        assert resp.success is True
        assert resp.data["metadata"]["content_type"] == "IMAGE"
        assert resp.data["metadata"]["analysis_mode"] == "full"


class TestMetricsOnlyMode:
    def test_no_media_metrics_only(self, analyst: ContentAnalystAgent):
        data = analyst._tiktok_or_raise().get_video("lk-001")
        assert data is not None
        analysis_input = ContentAnalysisInput(
            content_type=ContentType.VIDEO,
            content_metadata=data.video,
            performance_data=data.performance,
            comments=data.comments,
            media_source=None,
        )
        result = analyst.analyze_content(analysis_input)
        assert result.payload["metadata"]["analysis_mode"] == "metrics_only"
        assert result.payload.get("content_analysis") is None


class TestProviderSelection:
    def test_build_visual_provider_mock_default(self):
        provider = build_visual_provider()
        assert isinstance(provider, MockVisualProvider)

    def test_content_visual_analysis_service_routes_image(self):
        service = ContentVisualAnalysisService(MockVisualProvider())
        output = service.analyze_visual_content(
            content_type=ContentType.IMAGE,
            media_bytes=b"jpeg",
            mime_type="image/jpeg",
            context_json="{}",
        )
        assert output.content_type == ContentType.IMAGE
        assert output.image is not None


class TestAnalyzeContentAPI:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from app.main import app

        return TestClient(app)

    def test_content_analyze_endpoint(self, client):
        client.put(
            "/api/analytics/videos/lk-002/metrics",
            json={"views": 1000, "likes": 100, "comments": 10, "shares": 5, "saves": 20},
        )
        resp = client.post("/api/analytics/content/lk-002/analyze")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["metadata"]["content_type"] == "VIDEO"
