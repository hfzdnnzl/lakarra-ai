"""Tool abstraction.

Every capability an agent can invoke (TikTok, Canva, Playwright, Google Drive,
PostgreSQL, file storage, internal APIs, ...) implements the common
:class:`BaseTool` interface and returns a structured :class:`ToolResult`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Structured result returned by every tool invocation."""

    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class BaseTool(ABC):
    """Common interface for all tools."""

    #: Unique tool name used for lookup/registration.
    name: str = "base"
    #: Human-readable description of what the tool does.
    description: str = ""

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with structured keyword arguments."""

    def describe(self) -> dict[str, str]:
        return {"name": self.name, "description": self.description}
