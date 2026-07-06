"""Product Research Agent (Phase 1 mock).

Researches competitors and produces gap analysis and opportunities.
"""

from __future__ import annotations

from ...models.domain import Report
from ..base import AgentRequest, AgentResult, BaseAgent
from ..registry import register_agent


@register_agent
class ProductResearchAgent(BaseAgent):
    name = "product_research"
    role = "Product Research"
    description = "Researches competitors and identifies gaps and opportunities."

    def handle(self, request: AgentRequest) -> AgentResult:
        analysis = {
            "competitors": [
                {"name": "CompetitorA", "pricing": "$$", "positioning": "premium"},
                {"name": "CompetitorB", "pricing": "$", "positioning": "budget"},
            ],
            "gap_analysis": ["No fast turnaround option in market"],
            "opportunities": ["24h express card design", "AR preview of cards"],
        }

        self.context.memory.reports.add(
            Report(
                agent=self.name,
                title="Competitor gap analysis",
                summary="Mock competitor research.",
                payload=analysis,
            )
        )

        return AgentResult(
            agent=self.name,
            output=analysis,
            messages=["Produced mock gap analysis."],
        )
