"""Tests for unified VIDEO + IMAGE content analysis."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agents.content_analyst import ContentAnalystAgent
from app.config import effective_visual_analysis_provider, get_settings
from app.main import app
from app.models.content_analysis import ContentType
from app.providers import MockTikTokProvider, build_internal_content_provider
from app.repositories.analytics_repository import AnalyticsRepository
from app.services.analytics_service import AnalyticsService


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

    def test_video_recommendation_alias_maps_to_text(self):
        from app.models.content_analysis import VideoContentAnalysisSection

        section = VideoContentAnalysisSection(
            type="VIDEO",
            hook={
                "rating": "good",
                "score": 8,
                "confidence": "medium",
                "explanation": "Hook lands in the first second.",
                "recommendations": [
                    {
                        "recommendation": "Open with a stronger movement cue.",
                        "evidence": [
                            {
                                "source": "retention",
                                "description": "3-second hold dips after frame one.",
                            }
                        ],
                    }
                ],
            },
            story_script={
                "rating": "good",
                "score": 7,
                "confidence": "medium",
                "explanation": "Structure is clear.",
            },
            voiceover={
                "rating": "average",
                "score": 6,
                "confidence": "low",
                "explanation": "Voice pacing varies.",
            },
            pacing={
                "rating": "average",
                "score": 6,
                "confidence": "low",
                "explanation": "Middle section drags.",
            },
        )

        assert section.hook.recommendations[0].text == "Open with a stronger movement cue."

    def test_video_recommendation_malformed_items_are_dropped_not_fatal(self):
        """A single malformed recommendation (no usable text/evidence) must not fail the
        whole analysis — it should be dropped while well-formed siblings survive."""
        from app.models.content_analysis import VideoContentAnalysisSection

        section = VideoContentAnalysisSection(
            type="VIDEO",
            hook={
                "rating": "good",
                "score": 8,
                "confidence": "medium",
                "explanation": "Hook lands in the first second.",
                "recommendations": [
                    # No "text" and no recognized alias key at all.
                    {"unexpected_key": "Do something better."},
                    # Has text but no evidence — also unusable.
                    {"text": "Trim the intro by half a second."},
                    # Well-formed — should survive.
                    {
                        "text": "Open with a stronger movement cue.",
                        "evidence": [
                            {
                                "source": "retention",
                                "description": "3-second hold dips after frame one.",
                            }
                        ],
                    },
                ],
            },
            story_script={
                "rating": "good",
                "score": 7,
                "confidence": "medium",
                "explanation": "Structure is clear.",
            },
            voiceover={
                "rating": "average",
                "score": 6,
                "confidence": "low",
                "explanation": "Voice pacing varies.",
            },
            pacing={
                "rating": "average",
                "score": 6,
                "confidence": "low",
                "explanation": "Middle section drags.",
            },
        )

        assert len(section.hook.recommendations) == 1
        assert section.hook.recommendations[0].text == "Open with a stronger movement cue."

    def test_video_metrics_only(self, analytics_service: AnalyticsService):
        resp = analytics_service.analyze_content("lk-001", force=True)
        assert resp.success is False
        assert resp.error_type == "missing_media"

    def test_video_full_with_upload(self, analytics_service: AnalyticsService, db_session: Session):
        repo = AnalyticsRepository(db_session)
        repo.add_video_upload(
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
        assert resp.success is False
        assert resp.error_type == "missing_media"

    def test_image_full_with_upload(self, analytics_service: AnalyticsService, db_session: Session):
        repo = AnalyticsRepository(db_session)
        repo.add_video_upload(
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
        assert resp.status_code == 400
        assert "media" in resp.json()["detail"].lower()

    def test_legacy_video_endpoint_delegates(self, analytics_service: AnalyticsService):
        _ = analytics_service
        client = TestClient(app)
        resp = client.post("/api/analytics/videos/lk-002/analyze?force=true")
        assert resp.status_code == 400
        assert "media" in resp.json()["detail"].lower()

    def test_enum_synonym_and_default_coercion(self, caplog: pytest.LogCaptureFixture):
        from app.models.content_analysis import (
            CategoricalRating,
            Confidence,
            Evidence,
            EvidenceSource,
            Impact,
            RatedDimension,
            RootCause,
        )

        # 1. RatedDimension rating and confidence synonyms/defaults
        dim = RatedDimension.model_validate({
            "rating": "solid",
            "score": 7,
            "confidence": "certain",
            "explanation": "Valid explanation.",
        })
        assert dim.rating == CategoricalRating.GOOD
        assert dim.confidence == Confidence.HIGH

        dim_garbage = RatedDimension.model_validate({
            "rating": "garbage-rating-value",
            "score": 4,
            "confidence": "garbage-confidence-value",
            "explanation": "Valid explanation.",
        })
        assert dim_garbage.rating == CategoricalRating.AVERAGE
        assert dim_garbage.confidence == Confidence.MEDIUM
        assert any("content_analysis.enum_defaulted" in r.message for r in caplog.records)

        # 2. Evidence source synonyms/defaults
        caplog.clear()
        ev = Evidence.model_validate({
            "source": "retention_curve",
            "description": "Evidence description",
        })
        assert ev.source == EvidenceSource.RETENTION

        ev_garbage = Evidence.model_validate({
            "source": "some-junk-source",
            "description": "Evidence description",
        })
        assert ev_garbage.source == EvidenceSource.METRICS
        assert any("content_analysis.enum_defaulted" in r.message for r in caplog.records)

        # 3. RootCause impact and confidence synonyms/defaults
        caplog.clear()
        rc = RootCause.model_validate({
            "factor": "High load",
            "estimated_impact": "severe",
            "confidence": "tentative",
            "explanation": "Due to load.",
            "evidence": [{"source": "metrics", "description": "High cpu"}],
        })
        assert rc.estimated_impact == Impact.HIGH
        assert rc.confidence == Confidence.LOW

        rc_garbage = RootCause.model_validate({
            "factor": "High load",
            "estimated_impact": "junk-impact",
            "confidence": "junk-confidence",
            "explanation": "Due to load.",
            "evidence": [{"source": "metrics", "description": "High cpu"}],
        })
        assert rc_garbage.estimated_impact == Impact.MEDIUM
        assert rc_garbage.confidence == Confidence.MEDIUM
        assert any("content_analysis.enum_defaulted" in r.message for r in caplog.records)

    def test_required_text_hardening(self, caplog: pytest.LogCaptureFixture):
        from app.models.content_analysis import RootCause

        # Test RootCause string/null/empty coercion
        rc = RootCause.model_validate({
            "factor": "",  # empty
            "estimated_impact": "high",
            "confidence": "medium",
            "explanation": None,  # null
            "evidence": [{"source": "metrics", "description": 12345}],  # non-string description
        })
        assert rc.factor == "Unspecified root cause factor."
        assert rc.explanation == "Root cause explanation not provided."
        assert rc.evidence[0].description == "12345"
        assert any("content_analysis.text_defaulted" in r.message for r in caplog.records)
        assert any("content_analysis.text_normalized" in r.message for r in caplog.records)

    def test_root_cause_factor_alias_mapping_and_defaults(self):
        from app.models.content_analysis import RootCause

        # 1. Test factor resolves from 'text' or other alias when missing
        rc = RootCause.model_validate({
            "text": "Intro transitions are too abrupt.",
            "estimated_impact": "high",
            "confidence": "high",
            "explanation": "Many users left in first 2 seconds.",
            "evidence": [{"source": "retention", "description": "Abrupt scene drop-off."}],
        })
        assert rc.factor == "Intro transitions are too abrupt."

        # 2. Test default fallback value when no candidate at all
        rc_no_factor = RootCause.model_validate({
            "estimated_impact": "medium",
            "confidence": "medium",
            "explanation": "No explanation.",
            "evidence": [{"source": "metrics", "description": "Some issue"}],
        })
        assert rc_no_factor.factor == "Unspecified root cause factor."

    def test_performance_diagnosis_section_sanitizer(self):
        from app.models.content_analysis import PerformanceDiagnosisSection

        section = PerformanceDiagnosisSection.model_validate({
            "root_causes": [
                # Well-formed
                {
                    "factor": "Visual fatigue",
                    "estimated_impact": "high",
                    "confidence": "high",
                    "explanation": "Repetitive visuals are shown.",
                    "evidence": [{"source": "scene", "description": "Scene 3 repeats cover."}],
                },
                # Missing factor but has 'text'
                {
                    "text": "Intro transitions are too abrupt.",
                    "estimated_impact": "medium",
                    "confidence": "medium",
                    "explanation": "Many users left.",
                    "evidence": [{"source": "retention", "description": "Abrupt scene drop-off."}],
                },
                # Malformed — lacks evidence completely (should be dropped)
                {
                    "factor": "Sound levels too loud",
                    "estimated_impact": "low",
                    "confidence": "low",
                    "explanation": "Music drowns voice.",
                },
                # Malformed — neither factor nor text (should be dropped)
                {
                    "estimated_impact": "high",
                }
            ]
        })

        assert len(section.root_causes) == 2
        assert section.root_causes[0].factor == "Visual fatigue"
        assert section.root_causes[1].factor == "Intro transitions are too abrupt."
