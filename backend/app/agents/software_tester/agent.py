"""Software Tester Agent (Phase 1 mock).

Automatically tests the website (can use browser automation) and reports issues.
"""

from __future__ import annotations

from ...models.domain import Report
from ..base import AgentRequest, AgentResult, BaseAgent
from ..registry import register_agent


@register_agent
class SoftwareTesterAgent(BaseAgent):
    name = "software_tester"
    role = "Software Tester"
    description = "Runs automated website tests and reports bugs and issues."

    def handle(self, request: AgentRequest) -> AgentResult:
        findings = {
            "bugs": [],
            "broken_links": [],
            "layout_issues": [{"page": "/pricing", "issue": "CTA overlaps on mobile"}],
            "console_errors": [],
            "accessibility_issues": [{"page": "/", "issue": "Low contrast footer text"}],
        }

        self.context.memory.reports.add(
            Report(
                agent=self.name,
                title="Website test report",
                summary="Mock automated test report.",
                payload=findings,
            )
        )

        return AgentResult(
            agent=self.name,
            output=findings,
            messages=["Produced mock website test report."],
        )
