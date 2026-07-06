"""Deterministic mock LLM provider.

Returns structured, predictable responses so the whole platform runs without any
API keys or network access. This is the default provider during Phase 1.
"""

from __future__ import annotations

from .base import CompletionResult, LLMProvider, Message


class MockLLMProvider(LLMProvider):
    name = "mock"

    def complete(
        self, messages: list[Message], *, temperature: float = 0.7
    ) -> CompletionResult:
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "",
        )
        text = (
            "[mock-llm] This is a deterministic placeholder response. "
            f"Received {len(messages)} message(s). "
            f"Last user prompt: {last_user[:120]!r}"
        )
        return CompletionResult(
            text=text,
            model=self.model,
            provider=self.name,
            usage={"prompt_tokens": 0, "completion_tokens": 0},
        )
