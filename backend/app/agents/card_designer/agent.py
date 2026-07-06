"""Card Designer Agent (Phase 1 mock).

Generates wedding invitation design ideas as a structured design brief. Future
integration with Canva.
"""

from __future__ import annotations

from ...models.domain import Report
from ..base import AgentRequest, AgentResult, BaseAgent
from ..registry import register_agent


@register_agent
class CardDesignerAgent(BaseAgent):
    name = "card_designer"
    role = "Card Designer"
    description = "Generates wedding invitation design briefs (future Canva integration)."

    def handle(self, request: AgentRequest) -> AgentResult:
        design_brief = {
            "theme": "Modern botanical",
            "palette": ["#F7F3EE", "#5B6E52", "#C9A66B"],
            "typography": {"heading": "Cormorant Garamond", "body": "Inter"},
            "layout": "Portrait, single fold",
            "inspiration_sources": ["lakarra_templates", "pinterest", "trends_2026"],
            "canva_integration": "planned",
        }

        self.context.memory.reports.add(
            Report(
                agent=self.name,
                title="Card design brief",
                summary="Mock wedding invitation design brief.",
                payload=design_brief,
            )
        )

        return AgentResult(
            agent=self.name,
            output={"design_brief": design_brief},
            messages=["Produced mock design brief."],
        )
