"""
Multilingual **zero-shot** text moderation (Transformers) with a **deterministic rule fallback**.

Flow for ``moderate(text)``:

1. Empty / too-short OCR → fallback (no GPU transformer call).
2. Model unavailable at startup → degraded mode → fallback.
3. Otherwise run NLI zero-shot labels; **risk** uses max over harm labels only (educational/learning are separate). Threshold into ``safe``/``risky``/``dangerous``.
4. On inference errors → fallback so the API never crashes mid-request.

The fallback module is ``risk_scoring`` — tuned for OCR typos (fuzzy keywords + regex).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import importlib.util
import logging
import re
from time import perf_counter
import threading
from typing import Any

import torch
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

# Short names excluded from risk max / matched_keywords — CDC §4.3 educational NLI signals.
_EDU_SHORT_LABELS: frozenset[str] = frozenset({"educational", "learning"})
_RISK_LABEL_KEYS: frozenset[str] = frozenset(
    short for _hyp, short in ZERO_SHOT_LABELS if short not in _EDU_SHORT_LABELS
)

_classifier: Any = None
_startup_initialization_attempted = False
_degraded_mode = False
_degraded_reason = ""

# === Public data model ===


@dataclass(frozen=True)
class ModerationResult:
    """Structured output of ``moderate()`` — used by HTTP layer and offline evaluation."""
    matched_keywords: list[str]
    risk_score: float
    category: str
    display_text: str
    label_scores: dict[str, float]
    inference_ms: float
    used_fallback: bool
    educational_score: float = 0.0
    fallback_reason: str | None = None


# === Model/dependency initialization ===

def _build_classifier():
    """
    Construct the zero-shot classifier pipeline.

    Returns:
        Any: Hugging Face pipeline configured for local inference (GPU when available, CPU otherwise).
    """
    device = 0 if torch.cuda.is_available() else -1
    logger.info(
        "Zero-shot classifier device: %s",
        f"cuda:{device}" if device != -1 else "cpu",
    )
    classifier = pipeline(
        "zero-shot-classification",
        model=ZERO_SHOT_MODEL_NAME,
        tokenizer=ZERO_SHOT_MODEL_NAME,
        device=device,
    )
    logger.info("Moderation model running on GPU: %s", torch.cuda.is_available())
    return classifier


def _missing_dependencies() -> list[str]:
    """
    Detect missing runtime dependencies required by the zero-shot model.

    Returns:
        list[str]: Missing package names in pip-install format.
    """
    required_modules = (
        ("transformers", "transformers"),
        ("torch", "torch"),
        ("sentencepiece", "sentencepiece"),
        ("google.protobuf", "protobuf"),
    )
    missing = [name for module_name, name in required_modules if importlib.util.find_spec(module_name) is None]
    return missing


def _run_smoke_inference(classifier: Any) -> None:
    """
    Execute a tiny inference to validate model outputs after startup load.

    Args:
        classifier: Initialized Hugging Face zero-shot pipeline.

    Returns:
        None
    """
    smoke = classifier(
        "This is a harmless test sentence.",
        [hypothesis for hypothesis, _label in ZERO_SHOT_LABELS],
        multi_label=True,
        hypothesis_template=ZERO_SHOT_HYPOTHESIS_TEMPLATE,
    )
    if not isinstance(smoke, dict) or "scores" not in smoke:
        raise RuntimeError("smoke inference returned an unexpected output format")


def _build_classifier_with_timeout(timeout_seconds: int) -> Any:
    """
    Build classifier with a bounded startup wait.

    Args:
        timeout_seconds: Maximum number of seconds allowed for model loading.

    Returns:
        Any: Initialized Hugging Face classifier pipeline.
    """
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
    """
    Enable fallback-only degraded mode.

    Args:
        reason: Human-readable reason for degraded state.

    Returns:
        None
    """
    global _degraded_mode, _degraded_reason
    _degraded_mode = True
    _degraded_reason = reason


def _clear_degraded() -> None:
    """
    Clear degraded-mode flags after successful startup.

    Returns:
        None
    """
    global _degraded_mode, _degraded_reason
    _degraded_mode = False
    _degraded_reason = ""


def initialize_moderation() -> bool:
    """
    Called once at FastAPI startup. Returns ``True`` if the model loaded and smoke inference passed.

    On failure, sets **degraded** state so later calls use rule-only moderation.

    Returns:
        bool: True when model load + smoke inference succeed, False otherwise.
    """
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
    """
    Trigger one-time startup initialization when needed.

    Returns:
        None
    """
    if _startup_initialization_attempted:
        return
    initialize_moderation()


def get_classifier():
    """
    Return initialized classifier or raise when unavailable.

    Returns:
        Any: Ready zero-shot classifier.
    """
    _ensure_initialized()
    if _classifier is None:
        reason = _degraded_reason or "classifier unavailable"
        raise RuntimeError(reason)
    return _classifier


def is_classifier_ready() -> bool:
    """
    Report model readiness for production inference.

    Returns:
        bool: True when model weights are loaded and degraded mode is off.
    """
    _ensure_initialized()
    return _classifier is not None and not _degraded_mode


def category_from_model_score(score: float) -> str:
    """
    Convert numeric risk score to API category.

    Args:
        score: Risk score in [0, 1].

    Returns:
        str: One of ``safe``, ``risky``, ``dangerous``.
    """
    if score >= DANGEROUS_THRESHOLD:
        return "dangerous"
    if score >= RISKY_THRESHOLD:
        return "risky"
    return "safe"


def _normalized_text_length(text: str) -> int:
    """
    Count non-whitespace characters in OCR text.

    Args:
        text: OCR text candidate.

    Returns:
        int: Character count excluding whitespace.
    """
    return len(re.sub(r"\s+", "", text or ""))


def _label_scores_from_hf_raw(raw: dict[str, Any]) -> dict[str, float]:
    """
    Map raw Hugging Face output to internal moderation labels.

    Args:
        raw: Raw output from zero-shot pipeline.

    Returns:
        dict[str, float]: Internal label -> probability score.
    """
    labels = [str(label).strip() for label in raw.get("labels", [])]
    scores = [float(score) for score in raw.get("scores", [])]
    hypothesis_to_label = {hypothesis: label for hypothesis, label in ZERO_SHOT_LABELS}
    out: dict[str, float] = {}
    for hypothesis, score in zip(labels, scores):
        label = hypothesis_to_label.get(hypothesis)
        if label:
            out[label] = float(score)
    return out


def _educational_score_from_label_scores(label_scores: dict[str, float]) -> float:
    """
    Max NLI score for ``educational`` / ``learning`` hypotheses (CDC §4.3).

    Must use ``label_scores`` after classification — **not** ``matched_keywords`` from
    ``_extract_scores``, which only lists risk labels above ``MATCHED_KEYWORDS_THRESHOLD``.
    """
    edu = float(label_scores.get("educational", 0.0))
    learn = float(label_scores.get("learning", 0.0))
    return round(min(1.0, max(edu, learn)), 2)


def _cached_pairs_from_label_scores(label_scores: dict[str, float]) -> tuple[tuple[str, float], ...]:
    """
    Convert mutable dict scores into a stable tuple for caching.

    Args:
        label_scores: Internal label -> score mapping.

    Returns:
        tuple[tuple[str, float], ...]: Sorted key/value tuple.
    """
    return tuple(sorted(label_scores.items()))


@lru_cache(maxsize=CACHE_SIZE)
def _classify_zero_shot_cached(cleaned: str) -> tuple[tuple[str, float], ...]:
    """
    Run cached zero-shot moderation on cleaned OCR text.

    Args:
        cleaned: Stripped OCR text.

    Returns:
        tuple[tuple[str, float], ...]: Sorted moderation label-score tuples.
    """
    classifier = get_classifier()
    raw = classifier(
        cleaned,
        [hypothesis for hypothesis, _label in ZERO_SHOT_LABELS],
        multi_label=True,
        hypothesis_template=ZERO_SHOT_HYPOTHESIS_TEMPLATE,
    )
    label_scores = _label_scores_from_hf_raw(raw)
    return _cached_pairs_from_label_scores(label_scores)


def _extract_scores(label_scores: dict[str, float]) -> tuple[float, list[str]]:
    """
    Derive API-ready risk + matched labels from per-label scores.

    Educational / learning labels are omitted here so ``risk_score`` and ``matched_keywords``
    stay harm-oriented; use ``_educational_score_from_label_scores(label_scores)`` for §4.3.

    Args:
        label_scores: Internal label -> score mapping.

    Returns:
        tuple[float, list[str]]: Rounded risk score and sorted matched labels.
    """
    risk_only = {k: v for k, v in label_scores.items() if k in _RISK_LABEL_KEYS}
    risk_score = max(risk_only.values(), default=0.0)
    matched = [
        label
        for label, score in sorted(risk_only.items(), key=lambda item: item[1], reverse=True)
        if score >= MATCHED_KEYWORDS_THRESHOLD
    ]
    return round(min(1.0, risk_score), 2), matched


def _fallback_result(text: str, reason: str) -> ModerationResult:
    """
    Build a ``ModerationResult`` using deterministic fallback rules.

    Args:
        text: OCR text to analyze with fallback rules.
        reason: Why model path was skipped/failed.

    Returns:
        ModerationResult: Unified moderation result marked as fallback.
    """
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
        educational_score=0.0,
        fallback_reason=reason,
    )


def moderate(text: str) -> ModerationResult:
    """
    Public entry: classify OCR text (transformer or fallback).

    Prefer this for tests and ``evaluate_moderation.py``; HTTP uses ``analyze_text`` which wraps this.

    Args:
        text: OCR text.

    Returns:
        ModerationResult: Final moderation output used by API orchestration.
    """
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
        educational_score = _educational_score_from_label_scores(label_scores)
        return ModerationResult(
            matched_keywords=matched,
            risk_score=risk_score,
            category=category_from_model_score(risk_score),
            display_text=cleaned,
            label_scores=label_scores,
            inference_ms=inference_ms,
            used_fallback=False,
            educational_score=educational_score,
            fallback_reason=None,
        )
    except Exception as exc:
        logger.exception("Transformer moderation exception, using fallback rules: %s", exc)
        return _fallback_result(cleaned, f"exception during model inference: {exc}")


def analyze_text(text: str) -> RiskAnalysis:
    """
    Convert moderation output to legacy ``RiskAnalysis`` shape expected by orchestrator code.

    Args:
        text: OCR text.

    Returns:
        RiskAnalysis: Backward-compatible moderation payload.
    """
    result = moderate(text)
    return RiskAnalysis(
        matched_keywords=result.matched_keywords,
        risk_score=result.risk_score,
        display_text=result.display_text,
    )
