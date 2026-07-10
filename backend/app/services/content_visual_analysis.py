"""Multimodal visual analysis for VIDEO and IMAGE content."""

from __future__ import annotations

import base64
import json
import logging
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ..config import effective_visual_analysis_model, effective_visual_analysis_provider, get_settings
from ..errors import LLMCallError, MissingAPIKeyError
from ..models.content_analysis import ContentType, MediaSource
from ..services.ffmpeg_utils import resolve_ffmpeg_executable
from ..services.json_utils import extract_json

logger = logging.getLogger("lakarra.content_visual_analysis")


@dataclass
class VisualAnalysisContext:
    review_prompt: str
    plan_json: str = ""
    mode: str = "visual_analysis"  # visual_analysis | fidelity


class VisualContentProvider(ABC):
    @abstractmethod
    def analyze(
        self,
        *,
        content_type: ContentType,
        media: MediaSource,
        context: VisualAnalysisContext,
    ) -> str:
        """Return a JSON string matching the visual pass schema."""


class MockVisualProvider(VisualContentProvider):
    def analyze(
        self,
        *,
        content_type: ContentType,
        media: MediaSource,
        context: VisualAnalysisContext,
    ) -> str:
        plan = json.loads(context.plan_json) if context.plan_json else {}
        category = plan.get("category", "pov")
        is_fidelity = context.mode == "fidelity" or (
            "overall_match_score" in context.review_prompt
            or "plan-fidelity" in context.review_prompt.lower()
        )
        is_visual = (
            context.mode == "visual_analysis"
            or "visualpassoutput" in context.review_prompt.lower()
            or "pass 2 visual" in context.review_prompt.lower()
            or "content_analyst/visual" in context.review_prompt.lower()
        )
        is_performance = context.mode == "performance"

        if is_visual:
            from .analytics_mock import build_image_visual_pass_response, build_visual_pass_response

            if content_type == ContentType.IMAGE:
                return build_image_visual_pass_response()
            return build_visual_pass_response()

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


class GeminiVisualProvider(VisualContentProvider):
    _PROCESS_POLL_SECONDS = 2.0

    def analyze(
        self,
        *,
        content_type: ContentType,
        media: MediaSource,
        context: VisualAnalysisContext,
    ) -> str:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise MissingAPIKeyError(
                "GEMINI_API_KEY is not set. Configure it or set VISUAL_ANALYSIS_PROVIDER=mock."
            )

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover
            raise LLMCallError("The 'google-genai' package is not installed.") from exc

        if not media.bytes:
            raise LLMCallError("Gemini visual analysis requires media bytes.")

        client = genai.Client(api_key=settings.gemini_api_key)
        model = effective_visual_analysis_model(settings)
        max_wait = max(settings.llm_timeout_seconds, 120.0)
        mime_type = media.mime_type or (
            "image/jpeg" if content_type == ContentType.IMAGE else "video/mp4"
        )

        if content_type == ContentType.IMAGE:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        context.review_prompt,
                        f"Content plan JSON:\n{context.plan_json}" if context.plan_json else "",
                        types.Part.from_bytes(data=media.bytes, mime_type=mime_type),
                    ],
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
            except Exception as exc:  # noqa: BLE001
                raise LLMCallError(f"Gemini image analysis failed: {exc}") from exc
            text = getattr(response, "text", None) or ""
            if not text.strip():
                raise LLMCallError("Gemini returned an empty image analysis response.")
            return text

        suffix = ".mp4" if "mp4" in mime_type else ".mov" if "quicktime" in mime_type else ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(media.bytes)
            tmp_path = tmp.name

        try:
            uploaded = client.files.upload(
                file=tmp_path,
                config=types.UploadFileConfig(mime_type=mime_type),
            )
            uploaded = _wait_for_gemini_file(client, uploaded, max_wait=max_wait)
            response = client.models.generate_content(
                model=model,
                contents=[
                    context.review_prompt,
                    f"Content plan JSON:\n{context.plan_json}",
                    uploaded,
                ],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
        except LLMCallError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMCallError(f"Gemini video analysis failed: {exc}") from exc
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        text = getattr(response, "text", None) or ""
        if not text.strip():
            raise LLMCallError("Gemini returned an empty video analysis response.")
        return text


def _wait_for_gemini_file(client, uploaded, *, max_wait: float):
    deadline = time.monotonic() + max_wait
    current = uploaded
    while True:
        state = getattr(current, "state", None)
        state_name = getattr(state, "name", None) if state is not None else None
        if state_name == "ACTIVE":
            return current
        if state_name == "FAILED":
            raise LLMCallError("Gemini file processing failed.")
        if time.monotonic() >= deadline:
            raise LLMCallError("Gemini file processing timed out.")
        time.sleep(GeminiVisualProvider._PROCESS_POLL_SECONDS)
        current = client.files.get(name=current.name)


class OpenAIVisualProvider(VisualContentProvider):
    def analyze(
        self,
        *,
        content_type: ContentType,
        media: MediaSource,
        context: VisualAnalysisContext,
    ) -> str:
        settings = get_settings()
        if not settings.openai_api_key:
            raise MissingAPIKeyError(
                "OPENAI_API_KEY is not set. Configure it or set VISUAL_ANALYSIS_PROVIDER=mock."
            )
        if not media.bytes:
            raise LLMCallError("OpenAI visual analysis requires media bytes.")

        mime_type = media.mime_type or (
            "image/jpeg" if content_type == ContentType.IMAGE else "video/mp4"
        )

        if content_type == ContentType.IMAGE:
            frames = [media.bytes]
        else:
            frames = _sample_frames(media.bytes, mime_type)
            if not frames:
                raise LLMCallError(
                    "OpenAI video analysis could not extract frames from the upload."
                )

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMCallError("The 'openai' package is not installed.") from exc

        client = OpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)
        content_parts: list[dict] = [
            {
                "type": "text",
                "text": (
                    f"{context.review_prompt}\n\nContent plan JSON:\n{context.plan_json}"
                    if context.plan_json
                    else context.review_prompt
                ),
            },
        ]
        for frame in frames:
            b64 = base64.standard_b64encode(frame).decode("ascii")
            img_mime = mime_type if content_type == ContentType.IMAGE else "image/jpeg"
            content_parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{img_mime};base64,{b64}"},
                }
            )

        try:
            response = client.chat.completions.create(
                model=effective_visual_analysis_model(settings),
                messages=[{"role": "user", "content": content_parts}],
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMCallError(f"OpenAI visual analysis failed: {exc}") from exc

        text = response.choices[0].message.content if response.choices else ""
        if not text or not text.strip():
            raise LLMCallError("OpenAI returned an empty visual analysis response.")
        return text


def _sample_frames(video_bytes: bytes, mime_type: str) -> list[bytes]:
    ffmpeg = resolve_ffmpeg_executable()
    if ffmpeg is None:
        return []

    suffix = ".mp4" if "mp4" in mime_type else ".mov" if "quicktime" in mime_type else ".webm"
    frames: list[bytes] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / f"upload{suffix}"
        video_path.write_bytes(video_bytes)
        for i, t in enumerate((0, 3, 6, 9, 12)):
            out_path = Path(tmpdir) / f"frame_{i}.jpg"
            cmd = [
                ffmpeg,
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


class ContentVisualAnalysisService:
    def __init__(self, provider: VisualContentProvider | None = None) -> None:
        self._provider = provider or build_visual_provider()

    def analyze_visual(
        self,
        *,
        content_type: ContentType,
        media: MediaSource,
        context: VisualAnalysisContext,
    ) -> str:
        return self._provider.analyze(
            content_type=content_type,
            media=media,
            context=context,
        )

    def analyze_fidelity(
        self,
        *,
        video_bytes: bytes,
        mime_type: str,
        plan_json: str,
        review_prompt: str,
    ) -> str:
        """Plan-fidelity review for Content Creator (video uploads)."""

        return self._provider.analyze(
            content_type=ContentType.VIDEO,
            media=MediaSource(bytes=video_bytes, mime_type=mime_type),
            context=VisualAnalysisContext(
                review_prompt=review_prompt,
                plan_json=plan_json,
                mode="fidelity",
            ),
        )

    def analyze(
        self,
        *,
        video_bytes: bytes,
        mime_type: str,
        plan_json: str,
        review_prompt: str,
    ) -> str:
        """Legacy alias for plan-fidelity review."""

        return self.analyze_fidelity(
            video_bytes=video_bytes,
            mime_type=mime_type,
            plan_json=plan_json,
            review_prompt=review_prompt,
        )


def build_visual_provider() -> VisualContentProvider:
    provider = effective_visual_analysis_provider()
    if provider == "mock":
        return MockVisualProvider()
    if provider == "gemini":
        return GeminiVisualProvider()
    if provider == "openai":
        return OpenAIVisualProvider()
    raise ValueError(f"Unknown visual analysis provider: {provider}")


def build_content_visual_analysis_service() -> ContentVisualAnalysisService:
    return ContentVisualAnalysisService()


# Legacy aliases for Content Creator and transitional imports
VideoAnalysisService = ContentVisualAnalysisService


def build_video_analysis_service() -> ContentVisualAnalysisService:
    return build_content_visual_analysis_service()


def parse_review_json(text: str) -> dict:
    return extract_json(text)
