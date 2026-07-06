"""Tool registry.

A central registry lets agents discover tools by name. New tools can be added
without modifying existing agents: register the tool and reference it by name.
"""

from __future__ import annotations

from .base import BaseTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> BaseTool:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list(self) -> list[BaseTool]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return sorted(self._tools)


#: Process-wide tool registry.
registry = ToolRegistry()
