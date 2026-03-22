"""
Builds the **analyze** response from OCR text: moderation scores and API fields.

OCR runs in ``main.py`` (or callers) so HTTP can return a specific **OCR processing failed**
message without coupling to this module. ``build_analyze_response_from_plain_text`` is the
single place that combines ``analyze_text`` + ``category_from_model_score``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.moderation_service import analyze_text, category_from_model_score


@dataclass(frozen=True)
class ScreenshotAnalysisResult:
    """Fields align with the JSON contract consumed by the Node backend."""

    text: str
    display_text: str
    matched_keywords: list[str]
    risk_score: float
    category: str


def build_analyze_response_from_plain_text(raw: str) -> ScreenshotAnalysisResult:
    """Run text moderation on OCR output (may be empty)."""
    analysis = analyze_text(raw)
    risk_score = analysis.risk_score
    return ScreenshotAnalysisResult(
        text=raw,
        display_text=analysis.display_text,
        matched_keywords=analysis.matched_keywords,
        risk_score=risk_score,
        category=category_from_model_score(risk_score),
    )
