"""Configuration for local moderation and calibration."""

from __future__ import annotations

import os


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


ZERO_SHOT_MODEL_NAME = os.getenv(
    "MODERATION_MODEL_NAME",
    "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
)
ZERO_SHOT_HYPOTHESIS_TEMPLATE = os.getenv(
    "MODERATION_HYPOTHESIS_TEMPLATE",
    "This text contains {}.",
)

# Refined labels: no "safe content" label, because safe should be inferred by
# the absence of harmful high-confidence labels.
ZERO_SHOT_LABELS: tuple[tuple[str, str], ...] = (
    ("self-harm or suicide", "self-harm"),
    ("violence or physical harm", "violence"),
    ("hate speech or identity attack", "hate speech"),
    ("harassment or bullying", "harassment"),
    ("sexual content", "sexual content"),
    ("threat or intimidation", "threat"),
)

RISKY_THRESHOLD = _float_env("MODERATION_RISKY_THRESHOLD", 0.4)
DANGEROUS_THRESHOLD = _float_env("MODERATION_DANGEROUS_THRESHOLD", 0.85)
MATCHED_KEYWORDS_THRESHOLD = _float_env("MODERATION_MATCHED_KEYWORDS_THRESHOLD", 0.6)
SHORT_TEXT_FALLBACK_THRESHOLD = _int_env("MODERATION_SHORT_TEXT_FALLBACK_THRESHOLD", 5)
CACHE_SIZE = _int_env("MODERATION_CACHE_SIZE", 256)
STARTUP_MODEL_LOAD_TIMEOUT_SECONDS = _int_env("MODERATION_STARTUP_MODEL_LOAD_TIMEOUT_SECONDS", 20)
