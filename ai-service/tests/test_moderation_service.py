"""Unit tests for moderation_service.moderate() with mocks (no real model load)."""

from __future__ import annotations

import pytest

import app.services.moderation_service as ms


def test_moderate_empty_text_uses_fallback() -> None:
    r = ms.moderate("")
    assert r.used_fallback is True
    assert r.fallback_reason is not None
    assert "empty" in r.fallback_reason.lower()
    assert r.inference_ms == 0.0


def test_moderate_whitespace_only_uses_fallback() -> None:
    r = ms.moderate("   \n\t  ")
    assert r.used_fallback is True
    assert "empty" in (r.fallback_reason or "").lower()


def test_moderate_short_text_uses_fallback() -> None:
    # SHORT_TEXT_FALLBACK_THRESHOLD defaults to 5 non-whitespace chars
    r = ms.moderate("abcd")
    assert r.used_fallback is True
    assert "short" in (r.fallback_reason or "").lower()


def test_moderate_not_short_when_at_threshold_length(monkeypatch: pytest.MonkeyPatch) -> None:
    """Five non-whitespace characters should pass length gate (model path mocked)."""

    def fake_classify(_cleaned: str) -> tuple[tuple[str, float], ...]:
        return (("hate speech", 0.2),)

    monkeypatch.setattr(ms, "is_classifier_ready", lambda: True)
    monkeypatch.setattr(ms, "_classify_zero_shot_cached", fake_classify)

    r = ms.moderate("abcde")
    assert r.used_fallback is False


def test_moderate_classifier_not_ready_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ms, "is_classifier_ready", lambda: False)
    r = ms.moderate("this is long enough for the model path")
    assert r.used_fallback is True
    assert "ready" in (r.fallback_reason or "").lower() or "classifier" in (
        r.fallback_reason or ""
    ).lower()


def test_moderate_mocked_scores_risk_and_keywords(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_classify(_cleaned: str) -> tuple[tuple[str, float], ...]:
        return (
            ("hate speech", 0.95),
            ("violence", 0.55),
        )

    monkeypatch.setattr(ms, "is_classifier_ready", lambda: True)
    monkeypatch.setattr(ms, "_classify_zero_shot_cached", fake_classify)

    r = ms.moderate("some neutral long enough string here")
    assert r.used_fallback is False
    assert r.risk_score == 0.95
    assert "hate speech" in r.matched_keywords
    assert "violence" not in r.matched_keywords  # 0.55 < default keyword threshold 0.6
    assert r.category == "dangerous"


def test_moderate_mocked_risky_band(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_classify(_cleaned: str) -> tuple[tuple[str, float], ...]:
        return (("harassment", 0.5),)

    monkeypatch.setattr(ms, "is_classifier_ready", lambda: True)
    monkeypatch.setattr(ms, "_classify_zero_shot_cached", fake_classify)

    r = ms.moderate("another long enough string for moderation")
    assert r.used_fallback is False
    assert r.risk_score == 0.5
    assert r.category == "risky"


def test_moderate_inference_exception_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_cleaned: str) -> tuple[tuple[str, float], ...]:
        raise RuntimeError("pipeline exploded")

    monkeypatch.setattr(ms, "is_classifier_ready", lambda: True)
    monkeypatch.setattr(ms, "_classify_zero_shot_cached", boom)

    r = ms.moderate("long enough text that would normally hit the transformer")
    assert r.used_fallback is True
    assert r.fallback_reason is not None
    assert "exception" in r.fallback_reason.lower()
