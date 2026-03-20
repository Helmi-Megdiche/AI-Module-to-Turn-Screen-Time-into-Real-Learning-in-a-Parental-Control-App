"""OpenAI moderation wrapper with local fallback."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import math
import os
from pathlib import Path
from typing import Any
from urllib import error, request

from app.services.risk_scoring import RiskAnalysis, analyze_text as analyze_text_local

logger = logging.getLogger(__name__)

OPENAI_MODERATION_URL = "https://api.openai.com/v1/moderations"
DEFAULT_MODEL = "omni-moderation-latest"
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

# Heavier weights for immediately dangerous content.
CATEGORY_WEIGHTS: dict[str, float] = {
    "self-harm": 1.0,
    "self-harm/intent": 1.0,
    "self-harm/instructions": 1.0,
    "violence": 0.8,
    "violence/graphic": 0.9,
    "harassment": 0.35,
    "harassment/threatening": 0.8,
    "hate": 0.45,
    "hate/threatening": 0.85,
    "sexual": 0.35,
    "sexual/minors": 1.0,
    "illicit": 0.45,
    "illicit/violent": 0.85,
}

DISPLAY_LABELS: dict[str, str] = {
    "self-harm": "self-harm",
    "self-harm/intent": "self-harm intent",
    "self-harm/instructions": "self-harm instructions",
    "violence": "violence",
    "violence/graphic": "graphic violence",
    "harassment": "harassment",
    "harassment/threatening": "threatening harassment",
    "hate": "hate",
    "hate/threatening": "threatening hate",
    "sexual": "sexual",
    "sexual/minors": "sexual minors",
    "illicit": "illicit",
    "illicit/violent": "violent illicit",
}


@dataclass(frozen=True)
class ModerationConfig:
    api_key: str | None
    model: str
    enabled: bool


def _read_env_file_value(name: str) -> str | None:
    if not ENV_PATH.exists():
        return None

    prefix = f"{name}="
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        return value or None
    return None


def get_config() -> ModerationConfig:
    api_key = os.getenv("OPENAI_API_KEY") or _read_env_file_value("OPENAI_API_KEY")
    model = (
        os.getenv("OPENAI_MODERATION_MODEL")
        or _read_env_file_value("OPENAI_MODERATION_MODEL")
        or DEFAULT_MODEL
    ).strip() or DEFAULT_MODEL
    return ModerationConfig(api_key=api_key, model=model, enabled=bool(api_key))


def _post_moderation(text: str, config: ModerationConfig) -> dict[str, Any]:
    payload = {
        "model": config.model,
        "input": text,
    }
    req = request.Request(
        OPENAI_MODERATION_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _score_from_categories(category_scores: dict[str, float]) -> float:
    weighted_scores = [
        min(1.0, float(score) * CATEGORY_WEIGHTS[name])
        for name, score in category_scores.items()
        if name in CATEGORY_WEIGHTS
    ]
    if not weighted_scores:
        return 0.0
    return round(1 - math.prod(1 - score for score in weighted_scores), 2)


def _matched_labels(categories: dict[str, bool], category_scores: dict[str, float]) -> list[str]:
    matched = [
        DISPLAY_LABELS[name]
        for name, flagged in categories.items()
        if flagged and name in DISPLAY_LABELS
    ]
    if matched:
        return matched

    # If nothing crosses OpenAI's default flagged threshold, keep the top meaningful labels
    # so the UI still exposes why a medium-risk text was scored above zero.
    ranked = sorted(
        (
            (name, float(score))
            for name, score in category_scores.items()
            if name in DISPLAY_LABELS and float(score) >= 0.2
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    return [DISPLAY_LABELS[name] for name, _score in ranked[:3]]


def analyze_text(text: str) -> RiskAnalysis:
    if not text or not text.strip():
        return RiskAnalysis(matched_keywords=[], risk_score=0.0, display_text="")

    config = get_config()
    if not config.enabled:
        return analyze_text_local(text)

    try:
        body = _post_moderation(text, config)
        result = (body.get("results") or [None])[0] or {}
        categories = result.get("categories") or {}
        category_scores = result.get("category_scores") or {}
        return RiskAnalysis(
            matched_keywords=_matched_labels(categories, category_scores),
            risk_score=_score_from_categories(category_scores),
            display_text=text,
        )
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        logger.warning("OpenAI moderation failed (%s). Falling back to local rules. %s", exc.code, details)
    except Exception as exc:
        logger.warning("OpenAI moderation unavailable, falling back to local rules: %s", exc)

    return analyze_text_local(text)
