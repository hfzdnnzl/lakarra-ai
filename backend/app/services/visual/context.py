"""Shared context for visual analysis requests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VisualAnalysisContext:
    review_prompt: str
    plan_json: str = ""
    mode: str = "visual_analysis"  # visual_analysis | fidelity | performance
