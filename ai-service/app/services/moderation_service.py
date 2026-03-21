"""Local multilingual moderation service with rule-based fallback."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Any

from transformers import pipeline

from app.services.risk_scoring import RiskAnalysis, analyze_text as analyze_text_fallback

logger = logging.getLogger(__name__)

MODEL_NAME = "unitary/multilingual-toxic-xlm-roberta"
MATCH_THRESHOLD = 0.4
DANGEROUS_THRESHOLD = 0.75
RISKY_THRESHOLD = 0.4

_classifier: Any = None


@dataclass(frozen=True)
class ModerationResult:
    matched_keywords: list[str]
    risk_score: float
    category: str
    display_text: str


def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = pipeline(
            "text-classification",
            model=MODEL_NAME,
            return_all_scores=True,
            device=-1,
        )
    return _classifier


def category_from_model_score(score: float) -> str:
    if score >= DANGEROUS_THRESHOLD:
        return "dangerous"
    if score >= RISKY_THRESHOLD:
        return "risky"
    return "safe"


def _normalized_text_length(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def _extract_scores(raw_scores: list[dict[str, Any]]) -> tuple[float, list[str]]:
    matched: list[str] = []
    risk_score = 0.0

    for item in raw_scores:
        label = str(item.get("label", "")).lower().strip()
        score = float(item.get("score", 0.0))
        risk_score = max(risk_score, score)
        if score > MATCH_THRESHOLD:
            matched.append(label)

    return round(min(1.0, risk_score), 2), matched


def _to_risk_analysis(result: ModerationResult) -> RiskAnalysis:
    return RiskAnalysis(
        matched_keywords=result.matched_keywords,
        risk_score=result.risk_score,
        display_text=result.display_text,
    )


def analyze_text(text: str) -> RiskAnalysis:
    cleaned = (text or "").strip()
    if not cleaned:
        return analyze_text_fallback(text)

    # Very short OCR output is usually too noisy for a model-only decision.
    if _normalized_text_length(cleaned) < 5:
        return analyze_text_fallback(cleaned)

    try:
        classifier = get_classifier()
        raw_output = classifier(cleaned)
        raw_scores = raw_output[0] if raw_output and isinstance(raw_output[0], list) else raw_output
        risk_score, matched = _extract_scores(raw_scores or [])
        category = category_from_model_score(risk_score)
        return _to_risk_analysis(
            ModerationResult(
                matched_keywords=matched,
                risk_score=risk_score,
                category=category,
                display_text=cleaned,
            )
        )
    except Exception as exc:
        logger.warning("Transformer moderation failed, using fallback rules: %s", exc)
        return analyze_text_fallback(cleaned)
