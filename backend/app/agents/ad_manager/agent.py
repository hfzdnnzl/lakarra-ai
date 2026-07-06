"""Ad Manager Agent (Phase 1 mock).

Identifies which organic content should become paid ads and recommends budget and
scaling strategy.
"""

from __future__ import annotations

from ...models.domain import Report
from ..base import AgentRequest, AgentResult, BaseAgent
from ..registry import register_agent


@register_agent
class AdManagerAgent(BaseAgent):
    name = "ad_manager"
    role = "Ad Manager"
    description = "Recommends which organic content to boost into paid ads."

    def handle(self, request: AgentRequest) -> AgentResult:
        recommendation = {
            "boost_recommendation": True,
            "budget_recommendation": {"currency": "USD", "daily": 25},
            "scaling_strategy": "Increase 20% every 3 days while ROAS > 2.0",
            "kill_criteria": "Pause if CPA > $15 after $50 spend",
            "confidence_score": 0.62,
        }

        self.context.memory.reports.add(
            Report(
                agent=self.name,
                title="Ad boost recommendation",
                summary="Mock ad boost recommendation.",
                payload=recommendation,
            )
        )

        return AgentResult(
            agent=self.name,
            output=recommendation,
            messages=["Produced mock boost recommendation."],
        )
