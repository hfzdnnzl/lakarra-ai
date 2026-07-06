"""LLM provider abstraction.

Business logic depends only on :class:`LLMProvider`, never on a specific vendor
SDK. This lets the platform switch between OpenAI, Anthropic, Gemini or local
models without touching agent code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class CompletionResult:
    text: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)


class LLMProvider(ABC):
    """Common interface implemented by every LLM backend."""

    name: str = "base"

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    def complete(
        self, messages: list[Message], *, temperature: float = 0.7
    ) -> CompletionResult:
        """Return a completion for the given conversation."""
