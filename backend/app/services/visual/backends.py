"""LLM backends for multimodal visual analysis (provider-agnostic)."""

from __future__ import annotations

import base64
import json
import logging
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path

from ...config import effective_visual_analysis_model, effective_visual_analysis_provider, get_settings
from ...errors import LLMCallError, MissingAPIKeyError
from ...services.ffmpeg_utils import resolve_ffmpeg_executable
from .context import VisualAnalysisContext

logger = logging.getLogger("lakarra.visual.backends")


class VisualBackend(ABC):
    """Low-level multimodal completion — strategies decide what to attach."""

    @abstractmethod
    def complete_visual_json(
        self,
        prompt: str,
        *,
        plan_json: str = "",
        images: list[tuple[bytes, str]] | None = None,
        video: tuple[bytes, str] | None = None,
    ) -> str:
        """Return a JSON string from the vision model."""


class MockVisualBackend(VisualBackend):
    """Delegates non-visual modes to legacy mock responses."""

    def complete_visual_json(
        self,
        prompt: str,
        *,
        plan_json: str = "",
        images: list[tuple[bytes, str]] | None = None,
        video: tuple[bytes, str] | None = None,
    ) -> str:
        raise NotImplementedError(
            "MockVisualBackend.complete_visual_json should not be called directly; "
            "strategies supply deterministic mock JSON."
        )

    def complete_legacy_review(self, context: VisualAnalysisContext) -> str:
        plan = json.loads(context.plan_json) if context.plan_json else {}

        if context.mode == "fidelity" or (
            "overall_match_score" in context.review_prompt
            or "plan-fidelity" in context.review_prompt.lower()
        ):
            return self._fidelity_json(plan)

        return self._performance_json(plan)

    def _fidelity_json(self, plan: dict) -> str:
        category = plan.get("category", "pov")
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

    def _performance_json(self, plan: dict) -> str:
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


class GeminiVisualBackend(VisualBackend):
    _PROCESS_POLL_SECONDS = 2.0

    def complete_visual_json(
        self,
        prompt: str,
        *,
        plan_json: str = "",
        images: list[tuple[bytes, str]] | None = None,
        video: tuple[bytes, str] | None = None,
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

        client = genai.Client(api_key=settings.gemini_api_key)
        model = effective_visual_analysis_model(settings)
        max_wait = max(settings.llm_timeout_seconds, 120.0)

        parts: list = [prompt]
        if plan_json:
            parts.append(f"Content plan JSON:\n{plan_json}")

        if images:
            for data, mime in images:
                parts.append(types.Part.from_bytes(data=data, mime_type=mime))

        if video:
            data, mime_type = video
            suffix = ".mp4" if "mp4" in mime_type else ".mov" if "quicktime" in mime_type else ".webm"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            try:
                uploaded = client.files.upload(
                    file=tmp_path,
                    config=types.UploadFileConfig(mime_type=mime_type),
                )
                uploaded = _wait_for_gemini_file(client, uploaded, max_wait=max_wait)
                parts.append(uploaded)
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        try:
            response = client.models.generate_content(
                model=model,
                contents=parts,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMCallError(f"Gemini visual analysis failed: {exc}") from exc

        text = getattr(response, "text", None) or ""
        if not text.strip():
            raise LLMCallError("Gemini returned an empty visual analysis response.")
        return text


class OpenAIVisualBackend(VisualBackend):
    def complete_visual_json(
        self,
        prompt: str,
        *,
        plan_json: str = "",
        images: list[tuple[bytes, str]] | None = None,
        video: tuple[bytes, str] | None = None,
    ) -> str:
        settings = get_settings()
        if not settings.openai_api_key:
            raise MissingAPIKeyError(
                "OPENAI_API_KEY is not set. Configure it or set VISUAL_ANALYSIS_PROVIDER=mock."
            )

        frame_images: list[tuple[bytes, str]] = list(images or [])
        if video:
            data, mime_type = video
            sampled = _sample_frames(data, mime_type)
            if not sampled:
                raise LLMCallError("OpenAI video analysis could not extract frames from the upload.")
            frame_images.extend((frame, "image/jpeg") for frame in sampled)

        if not frame_images:
            raise LLMCallError("OpenAI visual analysis requires at least one image or video.")

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMCallError("The 'openai' package is not installed.") from exc

        client = OpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)
        content_parts: list[dict] = [
            {
                "type": "text",
                "text": f"{prompt}\n\nContent plan JSON:\n{plan_json}" if plan_json else prompt,
            },
        ]
        for frame, mime in frame_images:
            b64 = base64.standard_b64encode(frame).decode("ascii")
            content_parts.append(
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
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
        time.sleep(GeminiVisualBackend._PROCESS_POLL_SECONDS)
        current = client.files.get(name=current.name)


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


def build_visual_backend() -> VisualBackend:
    provider = effective_visual_analysis_provider()
    if provider == "mock":
        return MockVisualBackend()
    if provider == "gemini":
        return GeminiVisualBackend()
    if provider == "openai":
        return OpenAIVisualBackend()
    raise ValueError(f"Unknown visual analysis provider: {provider}")
