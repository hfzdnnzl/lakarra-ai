"""Tests for published media byte resolution."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.repositories.analytics_repository import AnalyticsRepository
from app.services.media_resolver import resolve_media_source, resolve_video_source


@pytest.fixture
def analytics_upload(db_session: Session) -> bytes:
    repo = AnalyticsRepository(db_session)
    repo.add_video_upload(
        video_id="lk-001",
        tiktok_handle="lakarra",
        storage_key="analytics/lk-001/test.mp4",
        mime_type="video/mp4",
        file_size=16,
        original_filename="take1.mp4",
    )
    db_session.commit()
    return b"fake-video-bytes"


class TestMediaResolver:
    def test_resolves_analytics_upload_first(
        self, db_session: Session, analytics_upload: bytes
    ):
        video_bytes = analytics_upload
        mock_storage = MagicMock()
        mock_storage.read_object.return_value = video_bytes

        with patch("app.services.media_resolver.get_storage", return_value=mock_storage):
            resolved = resolve_video_source(
                db_session,
                video_id="lk-001",
                tiktok_handle="lakarra",
            )

        assert resolved.source == "analytics_upload"
        assert resolved.bytes == video_bytes
        assert resolved.mime_type == "video/mp4"
        assert resolved.upload_id is not None

    def test_falls_back_to_none_when_no_upload_or_download(self, db_session: Session):
        with patch(
            "app.services.media_resolver.download_tiktok_video",
            return_value=None,
        ):
            resolved = resolve_media_source(
                db_session,
                post_id="lk-999",
                tiktok_handle="lakarra",
            )

        assert resolved.source == "none"
        assert resolved.bytes is None

    def test_tiktok_download_fallback(self, db_session: Session):
        with patch(
            "app.services.media_resolver.download_tiktok_video",
            return_value=(b"downloaded-bytes", "video/mp4", "https://cdn.example/v.mp4"),
        ):
            resolved = resolve_media_source(
                db_session,
                post_id="7658997469954559252",
                tiktok_handle="lakarra",
            )

        assert resolved.source == "remote_download"
        assert resolved.bytes == b"downloaded-bytes"
        assert resolved.download_url == "https://cdn.example/v.mp4"
