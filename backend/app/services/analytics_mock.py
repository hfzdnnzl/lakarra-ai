"""Deterministic mock responses for Content Analyst LLM prompts."""

from __future__ import annotations

import json
import re

from ..models.analytics import (
    CommentIntelligence,
    CompetitorAccountData,
    CompetitorAnalysisPayload,
    ContentAnalysisPayload,
    ContentRecommendations,
    EngagementMetrics,
    PatternAnalysisPayload,
    QualityScores,
    RetentionAnalysis,
    ReviewReportPayload,
    ScoreWithExplanation,
    TrendReportPayload,
)
from ..providers import TikTokVideoData


def _score(value: float, explanation: str) -> dict:
    return {"score": value, "explanation": explanation}


def build_video_analysis_response(
    video_data: TikTokVideoData,
    *,
    historical_context: str = "",
) -> str:
    v = video_data.video
    p = video_data.performance
    views = max(p.views, 1)
    engagement = EngagementMetrics(
        engagement_rate=round((p.likes + p.comments + p.shares + p.saves) / views, 4),
        share_rate=round(p.shares / views, 4),
        save_rate=round(p.saves / views, 4),
        like_to_view_ratio=round(p.likes / views, 4),
        comment_to_view_ratio=round(p.comments / views, 4),
        follower_conversion_rate=round(p.followers_gained / views, 4),
    )
    payload = ContentAnalysisPayload(
        video=v,
        performance=p,
        engagement=engagement,
        quality_scores=QualityScores(
            hook_score=_score_obj(0.78, "Strong opening visual with clear scroll-stop element"),
            retention_score=_score_obj(p.completion_rate, "Based on completion rate from metrics"),
            cta_score=_score_obj(0.65, "CTA present but could be more prominent"),
            pacing_score=_score_obj(0.72, "Good pacing for the duration"),
            storytelling_score=_score_obj(0.7, "Clear narrative arc"),
            emotional_impact=_score_obj(0.82, "Emotional resonance with target audience"),
            educational_value=_score_obj(
                0.55 if v.content_category != "educational" else 0.85,
                "Educational value varies by category",
            ),
            overall_content_health=_score_obj(0.74, "Solid performer with room for optimization"),
        ),
        retention=RetentionAnalysis(
            strongest_timestamp="0:02",
            weakest_timestamp=f"0:{max(v.duration - 5, 1):02d}",
            drop_off_points=["Mid-video transition", "Final 3 seconds"],
            pacing_issues=[] if p.completion_rate > 0.5 else ["Slow middle section"],
            scene_transition_issues=[],
        ),
        comments=CommentIntelligence(
            sentiment="positive",
            repeated_questions=["How much does this cost?", "Can I customize colors?"],
            feature_requests=["More template options", "Indian wedding themes"],
            customer_objections=["Prefer paper invites"],
            purchase_intent="moderate-high",
            most_common_keywords=["beautiful", "wedding", "customize", "link"],
        ),
        summary=f"Video '{v.title}' performed well with {p.views:,} views and "
        f"{engagement.engagement_rate:.1%} engagement rate.",
        strengths=[
            f"Engagement rate {engagement.engagement_rate:.1%} — above typical for this category",
            f"{p.saves:,} saves — strong bookmark intent",
            "Clear narrative arc keeps viewers through the middle",
        ],
        weaknesses=[
            "CTA could be more prominent in the final frame",
            "Hook text appears late — risk of early scroll-away",
            "Mid-video pacing slows when completion rate is below 50%",
        ],
        priority_improvements=[
            "Add bold on-screen hook text in the first 0.5 seconds",
            "Tighten mid-section cuts to improve completion rate",
            "End with a clearer verbal and visual CTA",
        ],
        recommendations=ContentRecommendations(
            content_categories=[v.content_category, "testimonial"],
            content_angles=["Before/after reveal", "Customer reaction"],
            hook_improvements=["Test question-format hooks", "Add text overlay in first 0.5s"],
            posting_schedule=["Friday 19:00", "Saturday 11:00"],
            experiments=["A/B test hook variants", "Try 15s vs 30s duration"],
            strategy_gaps=["Limited POV content", "No trend-jacking this week"],
        ),
    )
    return json.dumps(payload.model_dump(), indent=2)


def _score_obj(value: float, explanation: str) -> ScoreWithExplanation:
    return ScoreWithExplanation(score=round(value, 2), explanation=explanation)


def build_pattern_analysis_response(video_count: int) -> str:
    payload = PatternAnalysisPayload(
        best_performing_categories=["trend_adaptation", "educational", "testimonial"],
        best_posting_days=["Friday", "Saturday"],
        best_posting_times=["19:00", "11:00", "20:00"],
        best_duration="15-30 seconds",
        strongest_hooks=[
            "POV: your guests open the most beautiful invite",
            "Stop wasting money on paper invites",
            "Using this trend for wedding invites",
        ],
        common_failure_patterns=[
            "Videos over 45s lose retention",
            "Behind-the-scenes without clear payoff underperform",
            "Weak first-frame text overlay",
        ],
        recurring_successful_formats=[
            "Hook → reveal → CTA in under 30s",
            "Trend adaptation with brand twist",
            "Customer testimonial with emotional hook",
        ],
        summary=f"Analyzed {video_count} videos. Trend adaptation and educational "
        "content drive the highest engagement. Friday evening posts perform best.",
    )
    return json.dumps(payload.model_dump(), indent=2)


def build_competitor_analysis_response(account: CompetitorAccountData) -> str:
    payload = CompetitorAnalysisPayload(
        account=account,
        strengths=[
            f"Strong follower base ({account.follower_count:,})",
            f"Consistent posting ({account.posting_frequency})",
            "Diverse content categories",
        ],
        weaknesses=[
            "Lower engagement on long-form content",
            "Limited trend adaptation",
            "Generic CTA approach",
        ],
        opportunities=[
            "Lakarra can own the animated invite niche",
            "Competitor lacks POV-style content — opportunity for Lakarra",
            "Gap in multilingual content for Malaysian market",
        ],
        threats=[
            "Competitor's educational content drives high saves",
            "Established brand recognition",
        ],
        content_ideas=[
            "Animated invite vs competitor static approach comparison",
            "Malaysian wedding tradition meets digital invites",
            "Speed-run: full invite design in 60 seconds",
        ],
        summary=(
            f"Competitor @{account.handle} is strong in "
            f"{', '.join(account.content_categories[:2])} "
            "but leaves gaps in animation and localized content."
        ),
    )
    return json.dumps(payload.model_dump(), indent=2)


def build_review_response(content_title: str, category: str) -> str:
    payload = ReviewReportPayload(
        hook_strength=_score_obj(0.75, "Hook creates curiosity but could be more specific"),
        originality=_score_obj(0.68, "Familiar format with some unique brand elements"),
        pacing=_score_obj(0.8, "Well-paced for target duration"),
        emotional_trigger=_score_obj(0.72, "Touches on wedding emotion effectively"),
        clarity=_score_obj(0.85, "Message is clear and easy to follow"),
        audience_alignment=_score_obj(0.78, "Aligns with Malaysian couples 23-35"),
        cta=_score_obj(0.7, "CTA present but could be more urgent"),
        engagement_probability=_score_obj(0.73, "Above-average predicted engagement"),
        strengths=["Clear narrative", "Strong visual concept", "Good duration"],
        weaknesses=["Hook could be more provocative", "CTA lacks urgency"],
        suggestions=[
            "Test a question-format hook",
            "Add social proof element",
            "Strengthen CTA with time-sensitive language",
        ],
        confidence_score=0.76,
        approval_recommendation="approve",
    )
    return json.dumps(payload.model_dump(), indent=2)


def build_trend_report_response(period: str, patterns: PatternAnalysisPayload) -> str:
    payload = TrendReportPayload(
        period=period,
        patterns=patterns,
        recommendations=ContentRecommendations(
            content_categories=["trend_adaptation", "educational", "pov"],
            content_angles=["Cost comparison", "Emotional reveal", "Trend twist"],
            hook_improvements=["Question hooks", "Bold text overlay in frame 1"],
            posting_schedule=["Fri 19:00", "Sat 11:00"],
            experiments=["15s vs 30s", "Voiceover vs text-only"],
            strategy_gaps=["Underinvested in testimonial content"],
        ),
        account_health_score=0.72,
        growth_trend="steady upward",
        summary=f"Account health is good for period {period}. Focus on trend adaptation "
        "and Friday evening posting for maximum reach.",
    )
    return json.dumps(payload.model_dump(), indent=2)


def detect_analyst_prompt_type(system_text: str) -> str | None:
    lower = system_text.lower()
    if "analyze published tiktok videos" in lower:
        return "video"
    if "historical account performance" in lower:
        return "account"
    if "competitor tiktok accounts" in lower:
        return "competitor"
    if "review content plans" in lower:
        return "review"
    if "trend reports" in lower:
        return "trend"
    return None


def build_analyst_mock_response(system_text: str, user_text: str) -> str | None:
    """Return a mock analyst JSON response, or None if not an analyst prompt."""

    prompt_type = detect_analyst_prompt_type(system_text)
    if prompt_type is None:
        return None

    if prompt_type == "video":
        video_id_match = re.search(r'"video_id":\s*"([^"]+)"', user_text)
        title_match = re.search(r'"title":\s*"([^"]+)"', user_text)
        from ..providers import MockTikTokProvider

        provider = MockTikTokProvider("lakarra")
        vid = video_id_match.group(1) if video_id_match else "lk-001"
        data = provider.get_video(vid)
        if data is None:
            data = provider.get_account().videos[0]
        return build_video_analysis_response(data)

    if prompt_type == "account":
        from ..providers import MockTikTokProvider

        count = user_text.count("video_id")
        return build_pattern_analysis_response(max(count, 3))

    if prompt_type == "competitor":
        handle_match = re.search(r'"handle":\s*"([^"]+)"', user_text)
        from ..providers import MockCompetitorProvider

        handle = handle_match.group(1) if handle_match else "paperlesspost"
        account = MockCompetitorProvider().get_account(handle)
        return build_competitor_analysis_response(account)

    if prompt_type == "review":
        title_match = re.search(r"Title:\s*(.+)", user_text)
        cat_match = re.search(r"Category:\s*(\S+)", user_text)
        title = title_match.group(1).strip() if title_match else "Content"
        category = cat_match.group(1).strip() if cat_match else "aesthetic"
        return build_review_response(title, category)

    if prompt_type == "trend":
        period_match = re.search(r"period[:\s]+(\S+)", user_text, re.IGNORECASE)
        period = period_match.group(1) if period_match else "30d"
        patterns = PatternAnalysisPayload(
            best_performing_categories=["trend_adaptation", "educational"],
            best_posting_days=["Friday"],
            best_posting_times=["19:00"],
            best_duration="15-30s",
            strongest_hooks=["POV hooks perform best"],
            common_failure_patterns=["Long videos underperform"],
            recurring_successful_formats=["Hook-reveal-CTA"],
            summary="Steady growth with trend content leading.",
        )
        return build_trend_report_response(period, patterns)

    return None
