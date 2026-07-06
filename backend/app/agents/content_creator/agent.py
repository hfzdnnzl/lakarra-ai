"""Content Creator Agent (Phase 1 mock).

Generates new TikTok content using marketing strategy and analyst feedback.
"""

from __future__ import annotations

from ...models.domain import ContentIdea
from ..base import AgentRequest, AgentResult, BaseAgent
from ..registry import register_agent


@register_agent
class ContentCreatorAgent(BaseAgent):
    name = "content_creator"
    role = "Content Creator"
    description = "Generates TikTok content from strategy and analyst feedback."

    def handle(self, request: AgentRequest) -> AgentResult:
        idea = ContentIdea(
            title="Behind-the-scenes: designing a wedding invite",
            hook="POV: your dream wedding invite comes to life in 15 seconds",
            caption="Every card tells a love story. Here's how we craft yours. #wedding",
            hashtags=["#wedding", "#weddinginvitation", "#lakarra", "#behindthescenes"],
            payload={
                "scene_timeline": [
                    {"t": "0-3s", "scene": "Blank card + hook text"},
                    {"t": "3-10s", "scene": "Design montage"},
                    {"t": "10-15s", "scene": "Final reveal + CTA"},
                ],
                "voiceover": "Watch a plain card transform into a keepsake.",
                "on_screen_text": ["Your story", "Your design", "Your day"],
                "suggested_posting_time": "18:00",
            },
        )
        stored = self.context.memory.content.add(idea)

        return AgentResult(
            agent=self.name,
            output={"content_idea_id": stored.id, "content": stored.model_dump(mode="json")},
            messages=["Generated one mock content idea."],
        )
