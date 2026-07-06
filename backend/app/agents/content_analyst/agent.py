"""Content Analyst Agent (Phase 1 mock).

Analyzes existing TikTok content and critiques newly generated content. Produces
structured feedback only -- it never generates content.
"""

from __future__ import annotations

from ...models.domain import Report
from ..base import AgentRequest, AgentResult, BaseAgent
from ..registry import register_agent


@register_agent
class ContentAnalystAgent(BaseAgent):
    name = "content_analyst"
    role = "Content Analyst"
    description = "Analyzes TikTok performance and critiques content. Never creates content."

    def handle(self, request: AgentRequest) -> AgentResult:
        feedback = {
            "hook_strength": 0.7,
            "emotional_triggers": ["nostalgia", "excitement"],
            "why_it_worked": ["Strong 1s hook", "Clear payoff"],
            "why_it_failed": [],
            "common_patterns": ["Fast cuts", "Text-on-screen captions"],
            "best_posting_times": ["18:00", "20:00"],
        }

        self.context.memory.reports.add(
            Report(
                agent=self.name,
                title="Content analysis",
                summary="Mock structured content feedback.",
                payload=feedback,
            )
        )

        return AgentResult(
            agent=self.name,
            output={"feedback": feedback},
            messages=["Produced mock structured feedback."],
        )
