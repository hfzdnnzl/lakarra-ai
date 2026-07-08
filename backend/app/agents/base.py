"""Agent abstraction.

Every specialized agent inherits from :class:`BaseAgent` and communicates using
structured :class:`AgentRequest` / :class:`AgentResult` objects (typed JSON), not
free-form text. Agents receive an :class:`AgentContext` giving them access to
shared memory, the LLM provider and the tool registry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from ..memory import KeyValueStore, MemoryService
from ..services.llm import CompletionResult, LLMProvider, Message
from ..services.prompts import PromptTemplate, load_prompt
from ..tools import ToolRegistry


@dataclass
class AgentContext:
    """Shared dependencies injected into every agent."""

    memory: MemoryService
    llm: LLMProvider
    tools: ToolRegistry


class AgentRequest(BaseModel):
    """Structured input passed to an agent."""

    workflow: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Structured output returned by an agent."""

    agent: str
    status: str = "ok"
    output: dict[str, Any] = Field(default_factory=dict)
    messages: list[str] = Field(default_factory=list)


class BaseAgent(ABC):
    """Base class for all agents."""

    #: Unique agent identifier (used for routing/registration).
    name: str = "base"
    #: Human-readable role title.
    role: str = "Base Agent"
    #: Short description of the agent's responsibilities.
    description: str = ""
    #: Name of the prompt bundle under ``backend/prompts/`` (optional).
    prompt_name: str | None = None

    def __init__(self, context: AgentContext) -> None:
        self.context = context

    @property
    def private_memory(self) -> KeyValueStore:
        """The agent's private memory namespace."""

        return self.context.memory.namespace(self.name)

    @property
    def llm(self) -> LLMProvider:
        return self.context.llm

    # --- prompt + LLM helpers (shared by all agents) -----------------------
    def load_prompt(self) -> PromptTemplate:
        """Load this agent's prompt bundle from disk."""

        if not self.prompt_name:
            raise ValueError(f"Agent '{self.name}' has no prompt_name configured.")
        return load_prompt(self.prompt_name)

    def build_messages(self, **variables: str) -> list[Message]:
        """Render the agent's system + user prompts into LLM messages."""

        template = self.load_prompt()
        return [
            Message(role="system", content=template.system),
            Message(role="user", content=template.render_user(variables)),
        ]

    def complete(self, messages: list[Message], *, temperature: float = 0.7) -> CompletionResult:
        """Call the configured LLM provider."""

        return self.llm.complete(messages, temperature=temperature)

    @abstractmethod
    def handle(self, request: AgentRequest) -> AgentResult:
        """Process a structured request and return a structured result."""

    def describe(self) -> dict[str, str]:
        return {"name": self.name, "role": self.role, "description": self.description}
