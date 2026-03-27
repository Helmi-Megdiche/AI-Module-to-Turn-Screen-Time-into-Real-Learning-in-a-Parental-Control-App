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

from app import config
from app.services import vision_service
from app.services.dialect_utils import contains_risky_dialect
from app.services.moderation_service import category_from_model_score, moderate
from app.services.ocr_text_cleanup import clean_ocr_text

logger = logging.getLogger(__name__)

# When text+vision merge yields only "sexual content" above thresholds, raw scores can be
# falsely "dangerous" on noisy OCR; cap keeps parents alerted without max severity.
_SEXUAL_CONTENT_ONLY_CAP = 0.6


def _apply_sexual_content_safeguard(
    risk_score: float,
    matched_keywords: list[str],
) -> tuple[float, list[str]]:
    """
    If the only high-confidence label is ``sexual content`` and risk is at/above the
    dangerous threshold, cap risk at **0.6** (risky band) to reduce false positives.

    Multiple labels or any non-sexual keyword (e.g. vision, dialect) leaves the score unchanged.
    """
    if risk_score < config.DANGEROUS_THRESHOLD:
        return risk_score, matched_keywords
    if matched_keywords == ["sexual content"]:
        return _SEXUAL_CONTENT_ONLY_CAP, matched_keywords
    return risk_score, matched_keywords


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
    effective = raw
    if config.ENABLE_OCR_CLEANUP and raw:
        effective = clean_ocr_text(raw, digit_ratio_threshold=config.OCR_DIGIT_RATIO_THRESHOLD)

    text_mod = moderate(effective)
    dialect_risk, dialect_matches = contains_risky_dialect(effective)
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
    risk_score, matched_keywords = _apply_sexual_content_safeguard(
        risk_score,
        matched_keywords,
    )
    risk_score = round(risk_score, 2)
    return ScreenshotAnalysisResult(
        text=effective,
        display_text=text_mod.display_text,
        matched_keywords=matched_keywords,
        risk_score=risk_score,
        category=category_from_model_score(risk_score),
    )