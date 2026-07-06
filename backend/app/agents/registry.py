"""Agent registry.

Agents register themselves via the :func:`register_agent` decorator. This is the
mechanism that lets new agents be added *without modifying existing ones*: create
a new agent module, decorate the class, and import it in the package ``__init__``.
"""

from __future__ import annotations

from .base import AgentContext, BaseAgent


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, type[BaseAgent]] = {}

    def register(self, agent_cls: type[BaseAgent]) -> type[BaseAgent]:
        name = agent_cls.name
        if name in self._agents:
            raise ValueError(f"Agent already registered: {name}")
        self._agents[name] = agent_cls
        return agent_cls

    def get(self, name: str) -> type[BaseAgent] | None:
        return self._agents.get(name)

    def names(self) -> list[str]:
        return sorted(self._agents)

    def classes(self) -> list[type[BaseAgent]]:
        return list(self._agents.values())

    def instantiate(self, name: str, context: AgentContext) -> BaseAgent | None:
        agent_cls = self._agents.get(name)
        return agent_cls(context) if agent_cls else None

    def instantiate_all(self, context: AgentContext) -> dict[str, BaseAgent]:
        return {name: cls(context) for name, cls in self._agents.items()}


#: Process-wide agent registry.
registry = AgentRegistry()


def register_agent(agent_cls: type[BaseAgent]) -> type[BaseAgent]:
    """Class decorator that registers an agent in the global registry."""

    return registry.register(agent_cls)
