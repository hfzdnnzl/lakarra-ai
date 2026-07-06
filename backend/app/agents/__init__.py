"""Agent layer package.

Importing this package registers every built-in agent in the global registry.
To add a new agent: create ``app/agents/<name>/agent.py`` with a class decorated
by ``@register_agent`` and import it below. No existing agent needs to change.
"""

from __future__ import annotations

from ..memory import get_memory
from ..services.llm import get_llm
from ..tools import registry as tool_registry

# Import agent modules so their @register_agent decorators run.
from .ad_manager import AdManagerAgent  # noqa: E402,F401
from .base import AgentContext, AgentRequest, AgentResult, BaseAgent
from .card_designer import CardDesignerAgent  # noqa: E402,F401
from .ceo import CEOAgent  # noqa: E402,F401
from .content_analyst import ContentAnalystAgent  # noqa: E402,F401
from .content_creator import ContentCreatorAgent  # noqa: E402,F401
from .marketing_manager import MarketingManagerAgent  # noqa: E402,F401
from .product_research import ProductResearchAgent  # noqa: E402,F401
from .registry import registry
from .software_tester import SoftwareTesterAgent  # noqa: E402,F401

__all__ = [
    "AgentContext",
    "AgentRequest",
    "AgentResult",
    "BaseAgent",
    "registry",
    "get_agent_context",
]


def get_agent_context() -> AgentContext:
    """Build the shared agent context from configured dependencies."""

    return AgentContext(memory=get_memory(), llm=get_llm(), tools=tool_registry)
