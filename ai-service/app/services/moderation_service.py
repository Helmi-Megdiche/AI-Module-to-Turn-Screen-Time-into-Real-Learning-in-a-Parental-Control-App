"""Local multilingual moderation service with rule-based fallback."""

from __future__ import annotations

import logging
import re
from typing import Any

from transformers import pipeline

from app.services.risk_scoring import RiskAnalysis, analyze_text as analyze_text_fallback

logger = logging.getLogger(__name__)

MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
CANDIDATE_LABELS = [
    "self-harm",
    "violence",
    "hate speech",
    "harassment",
    "sexual content",
    "bullying",
    "threat",
    "safe content",
]
SAFE_LABEL = "safe content"
HYPOTHESIS_TEMPLATE = "This text contains {}."
MATCH_THRESHOLD = 0.4
DANGEROUS_THRESHOLD = 0.75
RISKY_THRESHOLD = 0.4

_classifier: Any = None


def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = pipeline(
            "zero-shot-classification",
            model=MODEL_NAME,
            tokenizer=MODEL_NAME,
            device=-1,
        )
        logger.info("Loaded moderation model: %s", MODEL_NAME)
    return _classifier


def category_from_model_score(score: float) -> str:
    if score >= DANGEROUS_THRESHOLD:
        return "dangerous"
    if score >= RISKY_THRESHOLD:
        return "risky"
    return "safe"


def _normalized_text_length(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def _extract_scores(result: dict[str, Any]) -> tuple[float, list[str]]:
    labels = [str(label).lower().strip() for label in result.get("labels", [])]
    scores = [float(score) for score in result.get("scores", [])]
    label_scores = dict(zip(labels, scores))

    harmful_scores = {
        label: score
        for label, score in label_scores.items()
        if label != SAFE_LABEL
    }
    risk_score = max(harmful_scores.values(), default=0.0)
    matched = [
        label
        for label, score in harmful_scores.items()
        if score >= MATCH_THRESHOLD
    ]
    return round(min(1.0, risk_score), 2), matched


def analyze_text(text: str) -> RiskAnalysis:
    cleaned = (text or "").strip()
    if not cleaned:
        logger.info("Fallback moderation: empty OCR text")
        return analyze_text_fallback(text)

    if _normalized_text_length(cleaned) < 5:
        logger.info("Fallback moderation: OCR text too short")
        return analyze_text_fallback(cleaned)

    try:
        classifier = get_classifier()
        result = classifier(
            cleaned,
            CANDIDATE_LABELS,
            multi_label=True,
            hypothesis_template=HYPOTHESIS_TEMPLATE,
        )
        risk_score, matched = _extract_scores(result or {})
        return RiskAnalysis(
            matched_keywords=matched,
            risk_score=risk_score,
            display_text=cleaned,
        )
    except Exception as exc:
        logger.warning("Transformer moderation failed, using fallback rules: %s", exc)
        return analyze_text_fallback(cleaned)
