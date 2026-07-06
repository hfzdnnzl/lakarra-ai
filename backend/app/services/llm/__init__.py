"""LLM service package: provider factory selected from configuration."""

from __future__ import annotations

from functools import lru_cache

from ...config import get_settings
from .base import CompletionResult, LLMProvider, Message
from .mock_provider import MockLLMProvider

__all__ = [
    "CompletionResult",
    "LLMProvider",
    "Message",
    "build_llm_provider",
    "get_llm",
]


def build_llm_provider() -> LLMProvider:
    """Instantiate the configured LLM provider."""

    settings = get_settings()
    provider = settings.llm_provider
    if provider == "mock":
        return MockLLMProvider(settings.llm_model)

    # Vendor providers are imported lazily to avoid importing heavy SDKs unless
    # they are actually selected.
    from .providers import AnthropicProvider, GeminiProvider, OpenAIProvider

    if provider == "openai":
        return OpenAIProvider(settings.llm_model, settings.openai_api_key)
    if provider == "anthropic":
        return AnthropicProvider(settings.llm_model, settings.anthropic_api_key)
    if provider == "gemini":
        return GeminiProvider(settings.llm_model, settings.gemini_api_key)
    raise ValueError(f"Unknown LLM provider: {provider}")


@lru_cache
def get_llm() -> LLMProvider:
    """Return the process-wide LLM provider (cached singleton)."""

    return build_llm_provider()
