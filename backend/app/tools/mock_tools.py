"""Mock tool implementations.

Phase 1 ships deterministic mock tools so agents and workflows can be exercised
end-to-end without external credentials or side effects. Replace the ``run``
bodies with real integrations in later phases.
"""

from __future__ import annotations

from typing import Any

from .base import BaseTool, ToolResult
from .registry import registry


class MockTool(BaseTool):
    """Generic mock tool that echoes its inputs back as structured data."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    def run(self, **kwargs: Any) -> ToolResult:
        return ToolResult(
            success=True,
            data={"tool": self.name, "echo": kwargs, "note": "mock implementation"},
        )


def register_default_tools() -> None:
    """Register the default set of mock tools (idempotent)."""

    defaults = [
        ("tiktok", "Read TikTok analytics and publish content (mock)."),
        ("canva", "Generate and edit designs in Canva (mock)."),
        ("playwright", "Drive a browser for automated website testing (mock)."),
        ("google_drive", "Read and write files in Google Drive (mock)."),
        ("postgres", "Run structured queries against PostgreSQL (mock)."),
        ("file_storage", "Store and retrieve files from object storage (mock)."),
        ("internal_api", "Call internal Lakarra service APIs (mock)."),
    ]
    for name, description in defaults:
        if registry.get(name) is None:
            registry.register(MockTool(name, description))


register_default_tools()
