"""
Builds the **analyze** response from OCR text: moderation scores and API fields.

OCR runs in ``main.py`` (or callers) so HTTP can return a specific **OCR processing failed**
message without coupling to this module. ``build_analyze_response_from_plain_text`` is the
single place that combines ``analyze_text`` + ``category_from_model_score``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from PIL import Image

from app.services import vision_service
from app.services.dialect_utils import contains_risky_dialect
from app.services.moderation_service import category_from_model_score, moderate

logger = logging.getLogger(__name__)


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
    dialect_risk, dialect_matches = contains_risky_dialect(raw)
    text_keywords = list(text_mod.matched_keywords)
    text_risk = float(text_mod.risk_score)
    if dialect_risk:
        logger.info("[DialectDetection] matches=%s", dialect_matches)
        text_keywords.extend(["tunisian_dialect_risk"] + dialect_matches)
        text_risk = min(1.0, text_risk + 0.1)

    vision_mod = vision_service.classify_image(image) if image is not None else {
        "riskScore": 0.0,
        "matchedKeywords": [],
    }

    vision_risk = float(vision_mod["riskScore"])
    risk_score = max(text_risk, vision_risk)
    matched_keywords = text_keywords + list(vision_mod["matchedKeywords"])
    return ScreenshotAnalysisResult(
        text=raw,
        display_text=text_mod.display_text,
        matched_keywords=matched_keywords,
        risk_score=round(risk_score, 2),
        category=category_from_model_score(risk_score),
    )