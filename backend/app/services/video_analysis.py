"""Multimodal video analysis for content review.

Compares an uploaded video against the generated content plan. Uses Gemini by
default (native video understanding); OpenAI falls back to sampled frames.
When ``VIDEO_ANALYSIS_PROVIDER=mock`` (the default), returns deterministic
structured JSON so the review pipeline works offline in tests.
"""

from __future__ import annotations

import base64
import json
import logging
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from ..config import get_settings
from ..errors import LLMCallError, MissingAPIKeyError
from ..services.json_utils import extract_json

logger = logging.getLogger("lakarra.video_analysis")


class VideoAnalysisService(ABC):
    @abstractmethod
    def analyze(
        self,
        *,
        video_bytes: bytes,
        mime_type: str,
        plan_json: str,
        review_prompt: str,
    ) -> str:
        """Return a JSON string matching the review schema."""


class MockVideoAnalysisService(VideoAnalysisService):
    def analyze(
        self,
        *,
        video_bytes: bytes,
        mime_type: str,
        plan_json: str,
        review_prompt: str,
    ) -> str:
        plan = json.loads(plan_json)
        category = plan.get("category", "pov")
        is_fidelity = (
            "overall_match_score" in review_prompt or "plan-fidelity" in review_prompt.lower()
        )

        if is_fidelity:
            return json.dumps(
                {
                    "overall_match_score": 0.82,
                    "hook_match": "The opening aligns with the planned hook concept.",
                    "scene_notes": [
                        "Scene pacing roughly matches the storyboard.",
                        "On-screen text appears close to the plan.",
                    ],
                    "voiceover_usage": (
                        "No voiceover required for this aesthetic plan."
                        if category == "aesthetic"
                        else "Voiceover lines largely follow the script."
                    ),
                    "cta_present": True,
                    "suggestions": ["Tighten the first-second hook for stronger scroll-stop."],
                    "summary": (
                        "Good overall fidelity to the generated plan with minor hook timing notes."
                    ),
                }
            )

        return json.dumps(
            {
                "hook_strength": 0.78,
                "emotional_triggers": ["aspiration", "excitement"],
                "pattern_match": "Matches fast-cut POV patterns seen in recent posts.",
                "compared_to_past_posts": [
                    "Similar hook structure to your last posted POV video.",
                    "Duration aligns with top-performing clips.",
                ],
                "posting_recommendation": plan.get("posting_time", "Friday 8:00 PM"),
                "confidence": 0.65,
                "summary": (
                    "Solid performance potential based on plan patterns and past post style."
                ),
            }
        )


class GeminiVideoAnalysisService(VideoAnalysisService):
    def analyze(
        self,
        *,
        video_bytes: bytes,
        mime_type: str,
        plan_json: str,
        review_prompt: str,
    ) -> str:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise MissingAPIKeyError(
                "GEMINI_API_KEY is not set. Configure it or set VIDEO_ANALYSIS_PROVIDER=mock."
            )

        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover
            raise LLMCallError(
                "The 'google-generativeai' package is not installed."
            ) from exc

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.video_analysis_model)

        suffix = ".mp4" if "mp4" in mime_type else ".mov" if "quicktime" in mime_type else ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        try:
            uploaded = genai.upload_file(tmp_path, mime_type=mime_type)
            response = model.generate_content(
                [
                    review_prompt,
                    f"Content plan JSON:\n{plan_json}",
                    uploaded,
                ],
                generation_config={"response_mime_type": "application/json"},
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMCallError(f"Gemini video analysis failed: {exc}") from exc
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        text = getattr(response, "text", None) or ""
        if not text.strip():
            raise LLMCallError("Gemini returned an empty video analysis response.")
        return text


class OpenAIVideoAnalysisService(VideoAnalysisService):
    """Sample a few frames with ffmpeg (when available) and send to GPT-4o vision."""

    def analyze(
        self,
        *,
        video_bytes: bytes,
        mime_type: str,
        plan_json: str,
        review_prompt: str,
    ) -> str:
        settings = get_settings()
        if not settings.openai_api_key:
            raise MissingAPIKeyError(
                "OPENAI_API_KEY is not set. Configure it or set VIDEO_ANALYSIS_PROVIDER=mock."
            )

        frames = _sample_frames(video_bytes, mime_type)
        if not frames:
            raise LLMCallError(
                "OpenAI video analysis requires ffmpeg to sample frames. "
                "Install ffmpeg or set VIDEO_ANALYSIS_PROVIDER=gemini."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMCallError("The 'openai' package is not installed.") from exc

        client = OpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)
        content_parts: list[dict] = [
            {"type": "text", "text": f"{review_prompt}\n\nContent plan JSON:\n{plan_json}"},
        ]
        for frame in frames:
            b64 = base64.standard_b64encode(frame).decode("ascii")
            content_parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                }
            )

        try:
            response = client.chat.completions.create(
                model=settings.model_name,
                messages=[{"role": "user", "content": content_parts}],
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMCallError(f"OpenAI frame analysis failed: {exc}") from exc

        text = response.choices[0].message.content if response.choices else ""
        if not text or not text.strip():
            raise LLMCallError("OpenAI returned an empty frame analysis response.")
        return text


def _sample_frames(video_bytes: bytes, mime_type: str) -> list[bytes]:
    suffix = ".mp4" if "mp4" in mime_type else ".mov" if "quicktime" in mime_type else ".webm"
    frames: list[bytes] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / f"upload{suffix}"
        video_path.write_bytes(video_bytes)
        for i, t in enumerate((0, 3, 6, 9, 12)):
            out_path = Path(tmpdir) / f"frame_{i}.jpg"
            cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                str(t),
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(out_path),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            except (FileNotFoundError, subprocess.SubprocessError):
                if i == 0:
                    return []
                break
            if out_path.exists():
                frames.append(out_path.read_bytes())
    return frames


def build_video_analysis_service() -> VideoAnalysisService:
    provider = get_settings().video_analysis_provider
    if provider == "mock":
        return MockVideoAnalysisService()
    if provider == "gemini":
        return GeminiVideoAnalysisService()
    if provider == "openai":
        return OpenAIVideoAnalysisService()
    raise ValueError(f"Unknown video analysis provider: {provider}")


def parse_review_json(text: str) -> dict:
    return extract_json(text)
