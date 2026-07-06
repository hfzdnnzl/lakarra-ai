"""Vendor LLM provider stubs (OpenAI, Anthropic, Gemini).

These are structural placeholders that share the :class:`LLMProvider` interface.
Wire the real SDK calls inside ``complete`` when API keys are configured. Keeping
them here (rather than importing heavy SDKs at module load) means the app boots
with only the mock provider active.
"""

from __future__ import annotations

from .base import CompletionResult, LLMProvider, Message


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str, api_key: str | None) -> None:
        super().__init__(model)
        self.api_key = api_key

    def complete(
        self, messages: list[Message], *, temperature: float = 0.7
    ) -> CompletionResult:
        raise NotImplementedError(
            "OpenAIProvider is a Phase 2 placeholder. Implement using the OpenAI "
            "SDK and OPENAI_API_KEY, or set LLM_PROVIDER=mock for development."
        )


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str, api_key: str | None) -> None:
        super().__init__(model)
        self.api_key = api_key

    def complete(
        self, messages: list[Message], *, temperature: float = 0.7
    ) -> CompletionResult:
        raise NotImplementedError(
            "AnthropicProvider is a Phase 2 placeholder. Implement using the "
            "Anthropic SDK and ANTHROPIC_API_KEY, or set LLM_PROVIDER=mock."
        )


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, model: str, api_key: str | None) -> None:
        super().__init__(model)
        self.api_key = api_key

    def complete(
        self, messages: list[Message], *, temperature: float = 0.7
    ) -> CompletionResult:
        raise NotImplementedError(
            "GeminiProvider is a Phase 2 placeholder. Implement using the Google "
            "Generative AI SDK and GEMINI_API_KEY, or set LLM_PROVIDER=mock."
        )
