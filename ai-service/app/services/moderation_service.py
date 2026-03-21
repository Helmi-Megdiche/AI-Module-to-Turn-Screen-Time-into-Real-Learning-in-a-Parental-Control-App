"""Local multilingual moderation service with rule-based fallback."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import importlib.util
import logging
import re
from time import perf_counter
import threading
from typing import Any

from transformers import pipeline

from app.config import (
    CACHE_SIZE,
    DANGEROUS_THRESHOLD,
    MATCHED_KEYWORDS_THRESHOLD,
    RISKY_THRESHOLD,
    SHORT_TEXT_FALLBACK_THRESHOLD,
    STARTUP_MODEL_LOAD_TIMEOUT_SECONDS,
    ZERO_SHOT_HYPOTHESIS_TEMPLATE,
    ZERO_SHOT_LABELS,
    ZERO_SHOT_MODEL_NAME,
)
from app.services.risk_scoring import RiskAnalysis, analyze_text as analyze_text_fallback

logger = logging.getLogger(__name__)

_classifier: Any = None
_startup_initialization_attempted = False
_degraded_mode = False
_degraded_reason = ""


@dataclass(frozen=True)
class ModerationResult:
    matched_keywords: list[str]
    risk_score: float
    category: str
    display_text: str
    label_scores: dict[str, float]
    inference_ms: float
    used_fallback: bool
    fallback_reason: str | None = None


def _build_classifier():
    return pipeline(
        "zero-shot-classification",
        model=ZERO_SHOT_MODEL_NAME,
        tokenizer=ZERO_SHOT_MODEL_NAME,
        device=-1,
    )


def _missing_dependencies() -> list[str]:
    required_modules = (
        ("transformers", "transformers"),
        ("torch", "torch"),
        ("sentencepiece", "sentencepiece"),
        ("google.protobuf", "protobuf"),
    )
    missing = [name for module_name, name in required_modules if importlib.util.find_spec(module_name) is None]
    return missing


def _run_smoke_inference(classifier: Any) -> None:
    smoke = classifier(
        "This is a harmless test sentence.",
        [hypothesis for hypothesis, _label in ZERO_SHOT_LABELS],
        multi_label=True,
        hypothesis_template=ZERO_SHOT_HYPOTHESIS_TEMPLATE,
    )
    if not isinstance(smoke, dict) or "scores" not in smoke:
        raise RuntimeError("smoke inference returned an unexpected output format")


def _build_classifier_with_timeout(timeout_seconds: int) -> Any:
    outcome: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            outcome["classifier"] = _build_classifier()
        except BaseException as exc:  # keep original error details
            error["exception"] = exc

    t = threading.Thread(target=_runner, name="moderation-startup-loader", daemon=True)
    t.start()
    t.join(timeout=max(1, timeout_seconds))

    if t.is_alive():
        raise TimeoutError(f"model loading exceeded {timeout_seconds}s timeout")
    if "exception" in error:
        raise RuntimeError(str(error["exception"])) from error["exception"]
    classifier = outcome.get("classifier")
    if classifier is None:
        raise RuntimeError("model loading returned no classifier")
    return classifier


def _set_degraded(reason: str) -> None:
    global _degraded_mode, _degraded_reason
    _degraded_mode = True
    _degraded_reason = reason


def _clear_degraded() -> None:
    global _degraded_mode, _degraded_reason
    _degraded_mode = False
    _degraded_reason = ""


def initialize_moderation() -> bool:
    global _classifier, _startup_initialization_attempted
    _startup_initialization_attempted = True
    try:
        missing = _missing_dependencies()
        if missing:
            raise RuntimeError(f"missing dependencies: {', '.join(missing)}")
        _classifier = _build_classifier_with_timeout(STARTUP_MODEL_LOAD_TIMEOUT_SECONDS)
        _run_smoke_inference(_classifier)
        _clear_degraded()
        logger.info("Loaded moderation model and smoke inference succeeded: %s", ZERO_SHOT_MODEL_NAME)
        return True
    except Exception as exc:
        _classifier = None
        _set_degraded(f"startup initialization failed: {exc}")
        logger.exception("Moderation startup failed; degraded fallback-only mode enabled: %s", exc)
        return False


def _ensure_initialized() -> None:
    if _startup_initialization_attempted:
        return
    initialize_moderation()


def get_classifier():
    _ensure_initialized()
    if _classifier is None:
        reason = _degraded_reason or "classifier unavailable"
        raise RuntimeError(reason)
    return _classifier


def is_classifier_ready() -> bool:
    _ensure_initialized()
    return _classifier is not None and not _degraded_mode


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
    logger.warning("Fallback moderation: %s", reason)
    fallback = analyze_text_fallback(text)
    return ModerationResult(
        matched_keywords=fallback.matched_keywords,
        risk_score=fallback.risk_score,
        category=category_from_model_score(fallback.risk_score),
        display_text=fallback.display_text,
        label_scores={},
        inference_ms=0.0,
        used_fallback=True,
        fallback_reason=reason,
    )


def moderate(text: str) -> ModerationResult:
    cleaned = (text or "").strip()
    if not cleaned:
        return _fallback_result(text, "empty OCR text")

    if _normalized_text_length(cleaned) < SHORT_TEXT_FALLBACK_THRESHOLD:
        return _fallback_result(cleaned, "OCR text too short")

    if not is_classifier_ready():
        return _fallback_result(cleaned, _degraded_reason or "classifier not ready")

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
            fallback_reason=None,
        )
    except Exception as exc:
        logger.exception("Transformer moderation exception, using fallback rules: %s", exc)
        return _fallback_result(cleaned, f"exception during model inference: {exc}")


def analyze_text(text: str) -> RiskAnalysis:
    result = moderate(text)
    return RiskAnalysis(
        matched_keywords=result.matched_keywords,
        risk_score=result.risk_score,
        display_text=result.display_text,
    )
