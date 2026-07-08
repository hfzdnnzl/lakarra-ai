"""Deterministic mock LLM provider.

Returns structured, predictable responses so the whole platform runs without any
API keys or network access. This is the default provider during development.

For content-generation prompts it parses the brief out of the user message and
returns a **valid** ``ContentIdea`` JSON payload, so the entire pipeline
(prompt -> LLM -> JSON parse -> validation -> structured model) is exercised.
"""

from __future__ import annotations

import json
import re

from .base import CompletionResult, LLMProvider, Message


def _extract(field: str, text: str) -> str:
    match = re.search(rf"^{re.escape(field)}:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def _looks_like_content_request(text: str) -> bool:
    return "business goal" in text.lower() and "json" in text.lower()


def _build_content_plan(user_text: str) -> str:
    goal = _extract("Business goal", user_text) or "Increase engagement"
    audience = _extract("Target audience", user_text) or "Malaysian couples aged 23-35"
    product = _extract("Product", user_text) or "Digital Wedding Invitation"

    plan = {
        "title": f"POV: Ditch the PDF for a {product}",
        "category": "pov",
        "target_audience": audience,
        "hook": "POV: your guests open your wedding invite and gasp",
        "duration": 15,
        "timeline": [
            {
                "start": 0,
                "end": 3,
                "scene": "Bride receives a boring PDF invite on WhatsApp",
                "camera": "Phone screen close-up",
                "text": "Masih guna PDF? 😬",
                "voiceover": "Still sending PDF invites?",
                "sound_effect": "notification ping",
            },
            {
                "start": 3,
                "end": 9,
                "scene": f"Reveal of an animated {product} with music and RSVP",
                "camera": "Slow zoom on phone, then over-the-shoulder",
                "text": "Upgrade to Lakarra ✨",
                "voiceover": "Meet your animated digital invitation.",
                "sound_effect": "sparkle swoosh",
            },
            {
                "start": 9,
                "end": 15,
                "scene": "Guests smiling, tapping RSVP, montage of happy reactions",
                "camera": "Quick cuts, handheld",
                "text": "RSVP in one tap",
                "voiceover": "Beautiful, effortless, unforgettable.",
                "sound_effect": "uplifting chime",
            },
        ],
        "music_suggestion": "Trending soft-romantic TikTok sound",
        "caption": f"{goal} — every love story deserves more than a PDF. 💍 #Lakarra",
        "hashtags": ["#wedding", "#weddinginvitation", "#lakarra", "#kahwin", "#fyp"],
        "cta": "Link in bio to design yours in minutes.",
        "posting_time": "Friday 8:00 PM",
        "confidence": 0.88,
    }
    return json.dumps(plan)


class MockLLMProvider(LLMProvider):
    name = "mock"

    def complete(
        self, messages: list[Message], *, temperature: float = 0.7
    ) -> CompletionResult:
        user_text = "\n".join(m.content for m in messages if m.role == "user")

        if _looks_like_content_request(user_text):
            text = _build_content_plan(user_text)
        else:
            text = (
                "[mock-llm] Deterministic placeholder response. "
                f"Received {len(messages)} message(s)."
            )

        # Rough token estimate (~4 chars/token) for realistic usage logging.
        prompt_chars = sum(len(m.content) for m in messages)
        return CompletionResult(
            text=text,
            model=self.model,
            provider=self.name,
            usage={
                "prompt_tokens": prompt_chars // 4,
                "completion_tokens": len(text) // 4,
                "total_tokens": (prompt_chars + len(text)) // 4,
            },
        )
