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
from app.services.ocr_text_cleanup import clean_ocr_text, should_keep_token

logger = logging.getLogger(__name__)

# Deterministic French harm phrases: mDeBERTa NLI often under-scores French threat hypotheses vs EN/AR.
FRENCH_DANGEROUS_HINTS = (
    "je vais te tuer",
    "je vais vous tuer",
    "je vais te frapper",
    "je vais te retrouver",
    "on va te retrouver",
    "tu vas mourir",
    "fabriquer une arme",
    "fabriquer un engin",
    "logiciel espion",
    "voler les données",
    "rejoins notre groupe",
    "par tous les moyens",
    "en finir avec ma vie",
    "vendre des drogues",
    "acheter de la drogue",
)

FRENCH_GROOMING_HINTS = (
    "viens chez moi",
    "donne moi ton numéro",
    "donne-moi ton numéro",
    "envoie moi ta photo",
    "envoie-moi une photo",
    "personne ne doit savoir",
    "c'est notre secret",
    "ne dis pas à tes parents",
    "ne le dis à personne",
    "rejoins moi en privé",
    "rejoins-moi en privé",
    "parle moi en privé",
    "tu es différente des autres",
    "tu es spéciale",
)

EDUCATIONAL_HINT_WORDS = (
    "learn",
    "learning",
    "study",
    "lesson",
    "tutorial",
    "explain",
    "explanation",
    "definition",
    "concept",
    "history",
    "science",
    "math",
    "grammar",
    "why",
    "how",
    "example",
    "apprentissage",
    "étudier",
    "étude",
    "étudie",
    "enseigner",
    "enseignement",
    "cours",
    "mathématiques",
    "mathématique",
    "sciences",
    "physique",
    "chimie",
    "biologie",
    "géographie",
    "littérature",
    "philosophie",
    "théorème",
    "formule",
    "équation",
    "algorithme",
    "révolution",
    "planète",
    "photosynthèse",
    "atome",
    "molécule",
    "adn",
    "système solaire",
    "cycle de l'eau",
    "droits de l'enfant",
    "تعلم",
    "تعليم",
    "درس",
    "دراسة",
    "رياضيات",
    "علوم",
    "فيزياء",
    "تاريخ",
    "جغرافيا",
    "النظام الشمسي",
    "كوكب",
    "شرح",
    "تعريف",
    "مثال",
    "histoire",
    "leçon",
    "apprendre",
    "expliquer",
)

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
    educational_score: float = 0.0


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
        cleaned = clean_ocr_text(raw, digit_ratio_threshold=config.OCR_DIGIT_RATIO_THRESHOLD)
        words = cleaned.split()
        filtered_words = [w for w in words if should_keep_token(w)]
        effective = " ".join(filtered_words)

    text_mod = moderate(effective)
    dialect_risk, dialect_matches = contains_risky_dialect(effective)
    text_keywords = list(text_mod.matched_keywords)
    text_risk = float(text_mod.risk_score)
    if dialect_risk:
        logger.info("[DialectDetection] matches=%s", dialect_matches)
        text_keywords.extend(["tunisian_dialect_risk"] + dialect_matches)
        if text_risk < 0.6:
            text_risk = min(1.0, text_risk + 0.3)
        else:
            text_risk = min(1.0, text_risk + 0.1)

    text_lower = effective.lower()
    if any(kw in text_lower for kw in FRENCH_DANGEROUS_HINTS):
        text_risk = max(text_risk, 0.92)
        if "french_dangerous_pattern" not in text_keywords:
            text_keywords.append("french_dangerous_pattern")
    elif any(kw in text_lower for kw in FRENCH_GROOMING_HINTS):
        text_risk = max(text_risk, 0.75)
        if "french_grooming_pattern" not in text_keywords:
            text_keywords.append("french_grooming_pattern")

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
    category = category_from_model_score(risk_score)

    # CDC §4.3 — after safeguard so capped risk (e.g. 0.6) drives threshold checks correctly.
    is_educational = text_mod.educational_score >= config.EDUCATIONAL_THRESHOLD
    edu_score = float(text_mod.educational_score)

    has_semantic_educational_hint = any(
        w in text_lower for w in EDUCATIONAL_HINT_WORDS
    )
    if (
        text_mod.educational_score >= 0.65
        and risk_score < config.RISKY_THRESHOLD
        and has_semantic_educational_hint
        and "educational content" not in matched_keywords
    ):
        matched_keywords.append("educational content")

    # RULE A — educational override (tightened)
    has_educational_signal = any(
        k in matched_keywords for k in ["educational content", "learning"]
    )
    if is_educational and risk_score < config.RISKY_THRESHOLD and has_educational_signal:
        category = "educational"

    # False-positive guard: when only educational signal is present, avoid escalating
    # to risky solely from noisy moderation scores.
    if (
        matched_keywords == ["educational content"]
        and category == "risky"
        and risk_score < config.DANGEROUS_THRESHOLD
    ):
        risk_score = min(risk_score, round(config.RISKY_THRESHOLD - 0.01, 2))
        category = "safe"

    # Keep educational_score meaningful, but suppress the boolean flag in clearly harmful
    # contexts so educational metrics do not over-report positives.
    harmful_keywords = [k for k in matched_keywords if k != "educational content"]
    if (
        category != "educational"
        and edu_score >= config.EDUCATIONAL_THRESHOLD
        and len(harmful_keywords) > 0
    ):
        edu_score = round(config.EDUCATIONAL_THRESHOLD - 0.01, 2)

    return ScreenshotAnalysisResult(
        text=effective,
        display_text=text_mod.display_text,
        matched_keywords=matched_keywords,
        risk_score=risk_score,
        category=category,
        educational_score=edu_score,
    )