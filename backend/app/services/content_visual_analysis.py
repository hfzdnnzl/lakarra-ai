"""Multimodal visual analysis for VIDEO and IMAGE published content."""

from __future__ import annotations

import base64
import logging
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from ..config import get_settings
from ..errors import LLMCallError, MissingAPIKeyError
from ..models.content_analysis import (
    ContentType,
    ImageContentAnalysis,
    RatedDimension,
    SceneAnalysis,
    VideoContentAnalysis,
    VisualPassOutput,
)
from ..services.json_utils import extract_json
from ..services.prompts import load_prompt

logger = logging.getLogger("lakarra.content_visual_analysis")


class VisualContentProvider(ABC):
    @abstractmethod
    def analyze(
        self,
        *,
        content_type: ContentType,
        media_bytes: bytes,
        mime_type: str,
        context_json: str,
    ) -> VisualPassOutput:
        """Run multimodal visual analysis for the given content type."""


def _rated(score: float, explanation: str) -> RatedDimension:
    return RatedDimension(score=score, explanation=explanation)


def _visual_provider_settings() -> tuple[str, str]:
    settings = get_settings()
    provider = settings.visual_analysis_provider or settings.video_analysis_provider
    model = settings.visual_analysis_model or settings.video_analysis_model
    return provider, model


class MockVisualProvider(VisualContentProvider):
    def analyze(
        self,
        *,
        content_type: ContentType,
        media_bytes: bytes,
        mime_type: str,
        context_json: str,
    ) -> VisualPassOutput:
        provider, model = _visual_provider_settings()
        if content_type == ContentType.IMAGE:
            return VisualPassOutput(
                content_type=ContentType.IMAGE,
                image=ImageContentAnalysis(
                    composition=_rated(0.82, "Balanced layout with clear focal point"),
                    typography=_rated(0.75, "Readable headline hierarchy"),
                    visual_hierarchy=_rated(0.8, "Message flows top-to-bottom naturally"),
                    branding=_rated(0.78, "Consistent Lakarra visual identity"),
                    message_clarity=_rated(0.85, "Wedding invite value prop is immediately clear"),
                    call_to_action=_rated(0.7, "CTA present but could be more prominent"),
                    visual_appeal=_rated(0.88, "Aesthetic aligns with target audience"),
                    color_harmony=_rated(0.83, "Warm palette supports emotional tone"),
                    scroll_stopping_potential=_rated(0.79, "Strong hero visual stops the scroll"),
                ),
                provider=provider,
                model=model,
                prompt_version="mock",
            )

        return VisualPassOutput(
            content_type=ContentType.VIDEO,
            video=VideoContentAnalysis(
                hook=_rated(0.8, "Opening frame creates immediate curiosity"),
                story_script="Hook → product reveal → social proof → CTA",
                voiceover="Conversational tone matching brand voice",
                scenes=[
                    SceneAnalysis(
                        timestamp="0:00",
                        description="Hook text overlay",
                        strength="strong",
                    ),
                    SceneAnalysis(
                        timestamp="0:05",
                        description="Product showcase",
                        strength="medium",
                    ),
                    SceneAnalysis(
                        timestamp="0:15",
                        description="CTA end card",
                        strength="medium",
                    ),
                ],
                pacing=_rated(0.76, "Cuts align with TikTok pacing norms"),
                storytelling=_rated(0.74, "Clear problem-solution arc"),
                visual_quality=_rated(0.81, "Sharp footage with consistent lighting"),
            ),
            provider=provider,
            model=model,
            prompt_version="mock",
        )


class GeminiVisualProvider(VisualContentProvider):
    def analyze(
        self,
        *,
        content_type: ContentType,
        media_bytes: bytes,
        mime_type: str,
        context_json: str,
    ) -> VisualPassOutput:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise MissingAPIKeyError(
                "GEMINI_API_KEY is not set. Configure it or set VISUAL_ANALYSIS_PROVIDER=mock."
            )

        prompt_name = (
            "content_analyst/visual/video"
            if content_type == ContentType.VIDEO
            else "content_analyst/visual/image"
        )
        template = load_prompt(prompt_name)
        user_prompt = template.render_user({"context_json": context_json})
        review_prompt = f"{template.system}\n\n{user_prompt}"

        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover
            raise LLMCallError("The 'google-generativeai' package is not installed.") from exc

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.visual_analysis_model)

        suffix = _suffix_for_mime(mime_type, content_type)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(media_bytes)
            tmp_path = tmp.name

        try:
            uploaded = genai.upload_file(tmp_path, mime_type=mime_type)
            response = model.generate_content(
                [review_prompt, uploaded],
                generation_config={"response_mime_type": "application/json"},
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMCallError(f"Gemini visual analysis failed: {exc}") from exc
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        text = getattr(response, "text", None) or ""
        if not text.strip():
            raise LLMCallError("Gemini returned an empty visual analysis response.")
        model_name = settings.visual_analysis_model or settings.video_analysis_model
        return _parse_visual_json(
            text, content_type, template.version, "gemini", model_name
        )


class OpenAIVisualProvider(VisualContentProvider):
    def analyze(
        self,
        *,
        content_type: ContentType,
        media_bytes: bytes,
        mime_type: str,
        context_json: str,
    ) -> VisualPassOutput:
        settings = get_settings()
        if not settings.openai_api_key:
            raise MissingAPIKeyError(
                "OPENAI_API_KEY is not set. Configure it or set VISUAL_ANALYSIS_PROVIDER=mock."
            )

        prompt_name = (
            "content_analyst/visual/video"
            if content_type == ContentType.VIDEO
            else "content_analyst/visual/image"
        )
        template = load_prompt(prompt_name)
        user_prompt = template.render_user({"context_json": context_json})
        review_prompt = f"{template.system}\n\n{user_prompt}"

        content_parts: list[dict] = [{"type": "text", "text": f"{review_prompt}\n\n{context_json}"}]

        if content_type == ContentType.IMAGE:
            b64 = base64.standard_b64encode(media_bytes).decode("ascii")
            content_parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                }
            )
        else:
            frames = _sample_frames(media_bytes, mime_type)
            if not frames:
                raise LLMCallError(
                    "OpenAI video visual analysis requires ffmpeg to sample frames."
                )
            for frame in frames:
                b64 = base64.standard_b64encode(frame).decode("ascii")
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    }
                )

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMCallError("The 'openai' package is not installed.") from exc

        client = OpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)
        try:
            response = client.chat.completions.create(
                model=settings.visual_analysis_model,
                messages=[{"role": "user", "content": content_parts}],
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMCallError(f"OpenAI visual analysis failed: {exc}") from exc

        text = response.choices[0].message.content if response.choices else ""
        if not text or not text.strip():
            raise LLMCallError("OpenAI returned an empty visual analysis response.")
        model_name = settings.visual_analysis_model or settings.video_analysis_model
        return _parse_visual_json(
            text, content_type, template.version, "openai", model_name
        )


def _suffix_for_mime(mime_type: str, content_type: ContentType) -> str:
    if content_type == ContentType.IMAGE:
        if "png" in mime_type:
            return ".png"
        if "webp" in mime_type:
            return ".webp"
        return ".jpg"
    if "mp4" in mime_type:
        return ".mp4"
    if "quicktime" in mime_type:
        return ".mov"
    return ".webm"


def _parse_visual_json(
    text: str,
    content_type: ContentType,
    prompt_version: str,
    provider: str,
    model: str,
) -> VisualPassOutput:
    data = extract_json(text)
    if content_type == ContentType.VIDEO:
        video = VideoContentAnalysis(**data.get("video", data))
        return VisualPassOutput(
            content_type=ContentType.VIDEO,
            video=video,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
        )
    image = ImageContentAnalysis(**data.get("image", data))
    return VisualPassOutput(
        content_type=ContentType.IMAGE,
        image=image,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
    )


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


class ContentVisualAnalysisService:
    """Routes visual analysis to the correct provider for VIDEO or IMAGE content."""

    def __init__(self, provider: VisualContentProvider | None = None) -> None:
        self._provider = provider or build_visual_provider()

    def analyze_visual_content(
        self,
        *,
        content_type: ContentType,
        media_bytes: bytes,
        mime_type: str,
        context_json: str,
    ) -> VisualPassOutput:
        return self._provider.analyze(
            content_type=content_type,
            media_bytes=media_bytes,
            mime_type=mime_type,
            context_json=context_json,
        )


def build_visual_provider() -> VisualContentProvider:
    provider, _ = _visual_provider_settings()
    if provider == "mock":
        return MockVisualProvider()
    if provider == "gemini":
        return GeminiVisualProvider()
    if provider == "openai":
        return OpenAIVisualProvider()
    raise ValueError(f"Unknown visual analysis provider: {provider}")


def build_content_visual_analysis_service() -> ContentVisualAnalysisService:
    return ContentVisualAnalysisService()


# Legacy CMS upload-review helpers (plan fidelity / performance prediction).
def parse_visual_json(text: str) -> dict:
    return extract_json(text)
