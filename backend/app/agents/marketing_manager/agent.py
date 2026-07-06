"""Marketing Manager Agent (Phase 1 mock).

Responsibilities: analyze content strategy, balance content categories, identify
weak areas and decide what content should be created.
"""

from __future__ import annotations

from ...models.domain import Report
from ..base import AgentRequest, AgentResult, BaseAgent
from ..registry import register_agent


@register_agent
class MarketingManagerAgent(BaseAgent):
    name = "marketing_manager"
    role = "Marketing Manager"
    description = "Owns content strategy and decides what content should be created."

    def handle(self, request: AgentRequest) -> AgentResult:
        content_requests = [
            {"topic": "Behind-the-scenes of card design", "category": "education"},
            {"topic": "Customer wedding story", "category": "emotional"},
        ]
        weekly_strategy = {
            "focus": "Balance educational and emotional content",
            "cadence": "1 post/day",
        }
        posting_schedule = [
            {"day": "Mon", "time": "18:00"},
            {"day": "Wed", "time": "12:00"},
            {"day": "Fri", "time": "20:00"},
        ]

        self.context.memory.reports.add(
            Report(
                agent=self.name,
                title="Weekly content strategy",
                summary="Mock weekly strategy and posting schedule.",
                payload={
                    "content_requests": content_requests,
                    "weekly_strategy": weekly_strategy,
                    "posting_schedule": posting_schedule,
                },
            )
        )

        return AgentResult(
            agent=self.name,
            output={
                "content_requests": content_requests,
                "weekly_strategy": weekly_strategy,
                "posting_schedule": posting_schedule,
            },
            messages=["Generated mock content strategy."],
        )
