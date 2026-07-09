"""Deterministic mock responses for Content Analyst LLM prompts."""

from __future__ import annotations

import json
import re

from ..models.analytics import (
    CompetitorAccountData,
    CompetitorAnalysisPayload,
    ContentRecommendations,
    PatternAnalysisPayload,
    ReviewReportPayload,
    ScoreWithExplanation,
    TrendReportPayload,
)
from ..models.content_analysis import (
    AudienceAnalysisSection,
    CategoricalRating,
    Confidence,
    ContentAnalysisSection,
    Evidence,
    EvidenceSource,
    Impact,
    MetricsPassOutput,
    PerformanceDiagnosisSection,
    RatedDimension,
    Recommendation,
    RecommendationsSection,
    RootCause,
    SceneAnalysis,
    VisualPassOutput,
)
from ..providers import TikTokVideoData


def _evidence(source: EvidenceSource, description: str) -> Evidence:
    return Evidence(source=source, description=description)


def _rec(text: str, source: EvidenceSource, description: str) -> Recommendation:
    return Recommendation(text=text, evidence=[_evidence(source, description)])


def _dimension(
    rating: CategoricalRating,
    score: int,
    confidence: Confidence,
    explanation: str,
    *,
    strengths: list[str] | None = None,
    weaknesses: list[str] | None = None,
) -> RatedDimension:
    return RatedDimension(
        rating=rating,
        score=score,
        confidence=confidence,
        explanation=explanation,
        strengths=strengths or [],
        weaknesses=weaknesses or [],
        recommendations=[],
    )


def build_video_analysis_response(
    video_data: TikTokVideoData,
    *,
    historical_context: str = "",
) -> str:
    v = video_data.video
    p = video_data.performance
    views = max(p.views, 1)
    save_rate = round(p.saves / views, 4)
    completion_pct = f"{p.completion_rate * 100:.1f}%"

    payload = MetricsPassOutput(
        audience_analysis=AudienceAnalysisSection(
            retention_summary=(
                f"Completion rate {completion_pct} with average watch "
                f"{p.average_watch_duration:.1f}s on a {v.duration}s video."
            ),
            strongest_timestamp="0:02" if p.completion_rate > 0.4 else "unknown",
            weakest_timestamp=f"0:{max(v.duration - 3, 1):02d}",
            drop_off_points=["Mid-video transition may lose viewers"],
            comment_sentiment="positive",
            repeated_questions=["How much does this cost?", "Can I customize colors?"],
            feature_requests=["More template options"],
            purchase_intent="moderate-high",
            audience_observations=[
                f"Save rate {save_rate:.1%} suggests bookmark intent",
                "Comments ask pricing questions — purchase consideration present",
            ],
        ),
        content_analysis_partial=ContentAnalysisSection(
            hook=_dimension(
                CategoricalRating.GOOD if p.completion_rate > 0.35 else CategoricalRating.WEAK,
                7 if p.completion_rate > 0.35 else 4,
                Confidence.MEDIUM,
                (
                    f"Early retention inferred from {completion_pct} completion — "
                    "hook likely holds initial attention"
                ),
                strengths=["Opening retains enough viewers to reach mid-video"],
                weaknesses=["Completion below 50% suggests hook could create more curiosity"],
            ),
            story_script=_dimension(
                CategoricalRating.GOOD,
                7,
                Confidence.LOW,
                "Story arc inferred from retention curve — visual confirmation unavailable",
            ),
            voiceover=_dimension(
                CategoricalRating.AVERAGE,
                5,
                Confidence.LOW,
                "No audio/visual evidence in metrics-only pass",
            ),
            pacing=_dimension(
                CategoricalRating.GOOD if p.completion_rate > 0.4 else CategoricalRating.AVERAGE,
                7 if p.completion_rate > 0.4 else 5,
                Confidence.MEDIUM,
                "Pacing inferred from completion and watch duration relative to video length",
            ),
            scenes=[],
        ),
        performance_diagnosis=PerformanceDiagnosisSection(
            root_causes=[
                RootCause(
                    factor="Hook curiosity gap",
                    estimated_impact=Impact.HIGH,
                    confidence=Confidence.MEDIUM,
                    explanation=(
                        f"Completion rate {completion_pct} with {p.average_watch_duration:.1f}s "
                        "average watch suggests viewers leave before the payoff."
                    ),
                    evidence=[
                        _evidence(
                            EvidenceSource.COMPLETION_RATE,
                            f"Completion rate is {completion_pct}",
                        ),
                        _evidence(
                            EvidenceSource.WATCH_DURATION,
                            f"Average watch {p.average_watch_duration:.1f}s vs {v.duration}s total",
                        ),
                    ],
                ),
                RootCause(
                    factor="Strong save intent",
                    estimated_impact=Impact.MEDIUM,
                    confidence=Confidence.HIGH,
                    explanation=(
                        f"Save rate {save_rate:.1%} indicates viewers want to revisit this content."
                    ),
                    evidence=[
                        _evidence(
                            EvidenceSource.METRICS,
                            f"{p.saves:,} saves on {p.views:,} views ({save_rate:.1%})",
                        ),
                    ],
                ),
            ]
        ),
        recommendations=RecommendationsSection(
            immediate_improvements=[
                _rec(
                    "Add bold on-screen hook text in the first 0.5 seconds",
                    EvidenceSource.COMPLETION_RATE,
                    f"Completion {completion_pct} — early drop-off likely",
                ),
            ],
            experiments=[
                _rec(
                    "Test revealing the final invitation in the first frame",
                    EvidenceSource.RETENTION,
                    "Retention drops before mid-video — curiosity hook may be weak",
                ),
            ],
            future_content_ideas=[
                _rec(
                    "Create a follow-up answering top pricing questions from comments",
                    EvidenceSource.COMMENTS,
                    "Repeated questions about cost in comments",
                ),
            ],
        ),
    )
    return json.dumps(payload.model_dump(mode="json"), indent=2)


def build_visual_pass_response() -> str:
    """Mock Pass 2 visual analysis output."""

    scene_rec = Recommendation(
        text="Add motion to the static product frame at 0:08",
        evidence=[_evidence(EvidenceSource.SCENE, "0:08 — Static product shot holds too long")],
    )
    payload = VisualPassOutput(
        content_analysis=ContentAnalysisSection(
            hook=RatedDimension(
                rating=CategoricalRating.GOOD,
                score=8,
                confidence=Confidence.HIGH,
                explanation="0:00 — Close-up product reveal creates immediate scroll-stop",
                strengths=["0:00 — Immediate product close-up creates scroll-stop"],
                weaknesses=["On-screen hook text appears after 1 second"],
                recommendations=[
                    Recommendation(
                        text="Move hook text to frame one",
                        evidence=[
                            _evidence(
                                EvidenceSource.SCENE,
                                "0:00 — Visual hook strong but text delayed",
                            )
                        ],
                    )
                ],
            ),
            story_script=RatedDimension(
                rating=CategoricalRating.GOOD,
                score=7,
                confidence=Confidence.MEDIUM,
                explanation="Clear before/after visual arc from reveal to CTA",
            ),
            voiceover=RatedDimension(
                rating=CategoricalRating.AVERAGE,
                score=6,
                confidence=Confidence.MEDIUM,
                explanation="Voiceover supports pacing but lacks urgency in the CTA",
            ),
            pacing=RatedDimension(
                rating=CategoricalRating.GOOD,
                score=7,
                confidence=Confidence.HIGH,
                explanation="Fast cuts in opening; slower middle section",
            ),
            scenes=[
                SceneAnalysis(
                    start_timestamp="0:00",
                    end_timestamp="0:03",
                    purpose="Hook — product close-up with title text",
                    effectiveness=CategoricalRating.EXCELLENT,
                    score=9,
                    confidence=Confidence.HIGH,
                    explanation="Strong scroll-stop visual with clear brand positioning",
                    recommendations=[],
                ),
                SceneAnalysis(
                    start_timestamp="0:03",
                    end_timestamp="0:08",
                    purpose="Product detail montage",
                    effectiveness=CategoricalRating.GOOD,
                    score=7,
                    confidence=Confidence.MEDIUM,
                    explanation="Quick cuts maintain momentum",
                    recommendations=[],
                ),
                SceneAnalysis(
                    start_timestamp="0:08",
                    end_timestamp="0:12",
                    purpose="CTA frame",
                    effectiveness=CategoricalRating.WEAK,
                    score=4,
                    confidence=Confidence.HIGH,
                    explanation="Static product shot with small CTA text",
                    recommendations=[scene_rec],
                ),
            ],
        ),
        performance_diagnosis=PerformanceDiagnosisSection(
            root_causes=[
                RootCause(
                    factor="Static mid-video frame",
                    estimated_impact=Impact.HIGH,
                    confidence=Confidence.HIGH,
                    explanation="0:08 — Static product shot likely causes retention drop",
                    evidence=[
                        _evidence(
                            EvidenceSource.SCENE,
                            "0:08 — No motion or new information for 3+ seconds",
                        )
                    ],
                ),
            ]
        ),
        recommendations=RecommendationsSection(
            immediate_improvements=[
                Recommendation(
                    text="Reduce static product shot below 2 seconds",
                    evidence=[
                        _evidence(
                            EvidenceSource.SCENE,
                            "0:08 — Static frame holds viewer attention poorly",
                        )
                    ],
                ),
            ],
            experiments=[
                Recommendation(
                    text="Try revealing the final invitation in the first frame",
                    evidence=[
                        _evidence(
                            EvidenceSource.SCENE,
                            "0:00 — Strong product visual could serve as payoff tease",
                        )
                    ],
                ),
            ],
        ),
    )
    return json.dumps(payload.model_dump(mode="json"), indent=2)


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
    if "metricspassoutput" in lower or "pass 1 metrics" in lower:
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
