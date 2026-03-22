"""
Builds the **analyze** response from OCR text: moderation scores and API fields.

OCR runs in ``main.py`` (or callers) so HTTP can return a specific **OCR processing failed**
message without coupling to this module. ``build_analyze_response_from_plain_text`` is the
single place that combines ``analyze_text`` + ``category_from_model_score``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PIL import Image

from app.services import vision_service
from app.services.moderation_service import category_from_model_score, moderate


@dataclass(frozen=True)
class ScreenshotAnalysisResult:
    """Fields align with the JSON contract consumed by the Node backend."""

    text: str
    display_text: str
    matched_keywords: list[str]
    risk_score: float
    category: str


def build_analyze_response_from_plain_text(
    raw: str,
    image: Optional[Image.Image] = None,
) -> ScreenshotAnalysisResult:
    """
    Run text moderation and optional visual moderation, then merge them.

    Final risk score uses the max of text and vision scores.
    """
    text_mod = moderate(raw)
    vision_mod = vision_service.classify_image(image) if image is not None else {
        "riskScore": 0.0,
        "matchedKeywords": [],
    }

    risk_score = max(float(text_mod.risk_score), float(vision_mod["riskScore"]))
    matched_keywords = text_mod.matched_keywords + list(vision_mod["matchedKeywords"])
    return ScreenshotAnalysisResult(
        text=raw,
        display_text=text_mod.display_text,
        matched_keywords=matched_keywords,
        risk_score=round(risk_score, 2),
        category=category_from_model_score(risk_score),
    )
