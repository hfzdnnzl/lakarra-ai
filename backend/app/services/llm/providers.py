"""Vendor LLM providers.

``OpenAIProvider`` is fully implemented (the one provider required this phase).
Anthropic and Gemini remain structural placeholders that share the
:class:`LLMProvider` interface, so they can be implemented later without touching
agent or service code.

Heavy vendor SDKs are imported lazily inside ``complete`` so the app boots with
only the mock provider active and no optional dependency installed.
"""

from __future__ import annotations

from ...errors import EmptyResponseError, LLMCallError, LLMTimeoutError, MissingAPIKeyError
from .base import CompletionResult, LLMProvider, Message


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str, api_key: str | None, *, timeout: float = 30.0) -> None:
        super().__init__(model)
        self.api_key = api_key
        self.timeout = timeout

    def complete(
        self, messages: list[Message], *, temperature: float = 0.7
    ) -> CompletionResult:
        if not self.api_key:
            raise MissingAPIKeyError(
                "OPENAI_API_KEY is not set. Configure it or set LLM_PROVIDER=mock."
            )

        try:
            from openai import APITimeoutError, OpenAI
        except ImportError as exc:  # pragma: no cover - depends on optional install
            raise LLMCallError(
                "The 'openai' package is not installed. Add it to run the OpenAI provider."
            ) from exc

        client = OpenAI(api_key=self.api_key, timeout=self.timeout)
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                response_format={"type": "json_object"},
            )
        except APITimeoutError as exc:
            raise LLMTimeoutError(f"OpenAI request timed out after {self.timeout}s.") from exc
        except Exception as exc:  # noqa: BLE001 - normalize any SDK/network error
            raise LLMCallError(f"OpenAI request failed: {exc}") from exc

        choice = response.choices[0] if response.choices else None
        text = (choice.message.content if choice and choice.message else None) or ""
        if not text.strip():
            raise EmptyResponseError("OpenAI returned an empty response.")

        usage = {}
        if response.usage is not None:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return CompletionResult(text=text, model=self.model, provider=self.name, usage=usage)


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str, api_key: str | None) -> None:
        super().__init__(model)
        self.api_key = api_key

    def complete(
        self, messages: list[Message], *, temperature: float = 0.7
    ) -> CompletionResult:
        raise NotImplementedError(
            "AnthropicProvider is a placeholder. Implement using the Anthropic SDK, "
            "or set LLM_PROVIDER=openai or mock."
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
            "GeminiProvider is a placeholder. Implement using the Google Generative AI "
            "SDK, or set LLM_PROVIDER=openai or mock."
        )
