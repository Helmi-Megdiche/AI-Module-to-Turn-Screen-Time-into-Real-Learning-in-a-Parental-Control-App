"""Local multilingual moderation service with rule-based fallback."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import logging
import re
from time import perf_counter
from typing import Any

from transformers import pipeline

from app.config import (
    CACHE_SIZE,
    DANGEROUS_THRESHOLD,
    MATCHED_KEYWORDS_THRESHOLD,
    RISKY_THRESHOLD,
    SHORT_TEXT_FALLBACK_THRESHOLD,
    ZERO_SHOT_HYPOTHESIS_TEMPLATE,
    ZERO_SHOT_LABELS,
    ZERO_SHOT_MODEL_NAME,
)
from app.services.risk_scoring import RiskAnalysis, analyze_text as analyze_text_fallback

logger = logging.getLogger(__name__)

_classifier: Any = None


@dataclass(frozen=True)
class ModerationResult:
    matched_keywords: list[str]
    risk_score: float
    category: str
    display_text: str
    label_scores: dict[str, float]
    inference_ms: float
    used_fallback: bool


def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = pipeline(
            "zero-shot-classification",
            model=ZERO_SHOT_MODEL_NAME,
            tokenizer=ZERO_SHOT_MODEL_NAME,
            device=-1,
        )
        logger.info("Loaded moderation model: %s", ZERO_SHOT_MODEL_NAME)
    return _classifier


def category_from_model_score(score: float) -> str:
    if score >= DANGEROUS_THRESHOLD:
        return "dangerous"
    if score >= RISKY_THRESHOLD:
        return "risky"
    return "safe"


def _normalized_text_length(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


@lru_cache(maxsize=CACHE_SIZE)
def _classify_zero_shot_cached(cleaned: str) -> tuple[tuple[str, float], ...]:
    classifier = get_classifier()
    raw = classifier(
        cleaned,
        [hypothesis for hypothesis, _label in ZERO_SHOT_LABELS],
        multi_label=True,
        hypothesis_template=ZERO_SHOT_HYPOTHESIS_TEMPLATE,
    )
    labels = [str(label).strip() for label in raw.get("labels", [])]
    scores = [float(score) for score in raw.get("scores", [])]
    hypothesis_to_label = {hypothesis: label for hypothesis, label in ZERO_SHOT_LABELS}
    mapped = []
    for hypothesis, score in zip(labels, scores):
        label = hypothesis_to_label.get(hypothesis)
        if label:
            mapped.append((label, float(score)))
    return tuple(mapped)


def _extract_scores(label_scores: dict[str, float]) -> tuple[float, list[str]]:
    risk_score = max(label_scores.values(), default=0.0)
    matched = [
        label
        for label, score in sorted(label_scores.items(), key=lambda item: item[1], reverse=True)
        if score >= MATCHED_KEYWORDS_THRESHOLD
    ]
    return round(min(1.0, risk_score), 2), matched


def _fallback_result(text: str, reason: str) -> ModerationResult:
    logger.info("Fallback moderation: %s", reason)
    fallback = analyze_text_fallback(text)
    return ModerationResult(
        matched_keywords=fallback.matched_keywords,
        risk_score=fallback.risk_score,
        category=category_from_model_score(fallback.risk_score),
        display_text=fallback.display_text,
        label_scores={},
        inference_ms=0.0,
        used_fallback=True,
    )


def moderate(text: str) -> ModerationResult:
    cleaned = (text or "").strip()
    if not cleaned:
        return _fallback_result(text, "empty OCR text")

    if _normalized_text_length(cleaned) < SHORT_TEXT_FALLBACK_THRESHOLD:
        return _fallback_result(cleaned, "OCR text too short")

    try:
        t0 = perf_counter()
        label_scores = dict(_classify_zero_shot_cached(cleaned))
        inference_ms = round((perf_counter() - t0) * 1000, 2)
        risk_score, matched = _extract_scores(label_scores)
        return ModerationResult(
            matched_keywords=matched,
            risk_score=risk_score,
            category=category_from_model_score(risk_score),
            display_text=cleaned,
            label_scores=label_scores,
            inference_ms=inference_ms,
            used_fallback=False,
        )
    except Exception as exc:
        logger.warning("Transformer moderation failed, using fallback rules: %s", exc)
        return _fallback_result(cleaned, f"model error: {exc}")


def analyze_text(text: str) -> RiskAnalysis:
    result = moderate(text)
    return RiskAnalysis(
        matched_keywords=result.matched_keywords,
        risk_score=result.risk_score,
        display_text=result.display_text,
    )
