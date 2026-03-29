"""Educational NLI (CDC §4.3): moderation scoring and orchestrator category fusion."""

from __future__ import annotations

import pytest

import app.services.moderation_service as ms
from app import config
from app.services.analysis_orchestrator import build_analyze_response_from_plain_text
import app.services.analysis_orchestrator as orch
from app.services.moderation_service import ModerationResult

LONG_TEXT = "this text is long enough for the moderation model path"


def test_moderate_educational_label_scores_high_educational_score(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_classify(_cleaned: str) -> tuple[tuple[str, float], ...]:
        return tuple(
            sorted(
                {
                    "educational": 0.75,
                    "learning": 0.4,
                    "violence": 0.1,
                    "hate speech": 0.05,
                }.items()
            )
        )

    monkeypatch.setattr(ms, "is_classifier_ready", lambda: True)
    monkeypatch.setattr(ms, "_classify_zero_shot_cached", fake_classify)

    result = ms.moderate(LONG_TEXT)
    assert result.used_fallback is False
    assert result.educational_score >= config.EDUCATIONAL_THRESHOLD
    assert result.educational_score == 0.75


def test_moderate_educational_below_threshold_not_boosted(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_classify(_cleaned: str) -> tuple[tuple[str, float], ...]:
        return tuple(sorted({"educational": 0.4, "learning": 0.3}.items()))

    monkeypatch.setattr(ms, "is_classifier_ready", lambda: True)
    monkeypatch.setattr(ms, "_classify_zero_shot_cached", fake_classify)

    result = ms.moderate(LONG_TEXT)
    assert result.used_fallback is False
    assert result.educational_score == 0.4
    assert result.educational_score < config.EDUCATIONAL_THRESHOLD


def test_moderate_risky_text_educational_score_low_and_risk_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_classify(_cleaned: str) -> tuple[tuple[str, float], ...]:
        return tuple(sorted({"violence": 0.8, "educational": 0.1}.items()))

    monkeypatch.setattr(ms, "is_classifier_ready", lambda: True)
    monkeypatch.setattr(ms, "_classify_zero_shot_cached", fake_classify)

    result = ms.moderate(LONG_TEXT)
    assert result.used_fallback is False
    assert result.risk_score >= 0.8
    assert result.educational_score == 0.1
    assert result.category != "educational"


def test_moderate_empty_text_educational_score_zero() -> None:
    result = ms.moderate("")
    assert result.educational_score == 0.0


def test_orchestrator_educational_low_risk_sets_category_educational(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_moderate(_text: str) -> ModerationResult:
        return ModerationResult(
            matched_keywords=[],
            risk_score=0.2,
            category="safe",
            display_text="",
            label_scores={},
            inference_ms=0.0,
            used_fallback=False,
            educational_score=0.7,
        )

    monkeypatch.setattr(orch, "moderate", fake_moderate)

    out = build_analyze_response_from_plain_text(LONG_TEXT, image=None)
    assert out.category == "educational"
    assert "educational content" in out.matched_keywords
    assert out.educational_score == 0.7


def test_orchestrator_educational_high_risk_surfaces_signal_not_category(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_moderate(_text: str) -> ModerationResult:
        return ModerationResult(
            matched_keywords=[],
            risk_score=0.65,
            category="risky",
            display_text="",
            label_scores={},
            inference_ms=0.0,
            used_fallback=False,
            educational_score=0.7,
        )

    monkeypatch.setattr(orch, "moderate", fake_moderate)

    out = build_analyze_response_from_plain_text(LONG_TEXT, image=None)
    assert out.category != "educational"
    assert "educational content" in out.matched_keywords
    assert out.educational_score == 0.7


def test_orchestrator_non_educational_never_educational_category(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_moderate(_text: str) -> ModerationResult:
        return ModerationResult(
            matched_keywords=[],
            risk_score=0.1,
            category="safe",
            display_text="",
            label_scores={},
            inference_ms=0.0,
            used_fallback=False,
            educational_score=0.1,
        )

    monkeypatch.setattr(orch, "moderate", fake_moderate)

    out = build_analyze_response_from_plain_text(LONG_TEXT, image=None)
    assert out.category != "educational"
    assert "educational content" not in out.matched_keywords


def test_orchestrator_educational_score_always_present(monkeypatch: pytest.MonkeyPatch) -> None:
    scenarios = [
        ModerationResult(
            matched_keywords=[],
            risk_score=0.1,
            category="safe",
            display_text="",
            label_scores={},
            inference_ms=0.0,
            used_fallback=False,
            educational_score=0.1,
        ),
        ModerationResult(
            matched_keywords=[],
            risk_score=0.65,
            category="risky",
            display_text="",
            label_scores={},
            inference_ms=0.0,
            used_fallback=False,
            educational_score=0.7,
        ),
        ModerationResult(
            matched_keywords=[],
            risk_score=0.2,
            category="safe",
            display_text="",
            label_scores={},
            inference_ms=0.0,
            used_fallback=False,
            educational_score=0.7,
        ),
    ]

    for mod in scenarios:

        def _m(_t: str, fixed: ModerationResult = mod) -> ModerationResult:
            return fixed

        monkeypatch.setattr(orch, "moderate", _m)
        out = build_analyze_response_from_plain_text(LONG_TEXT, image=None)
        assert hasattr(out, "educational_score")
        assert isinstance(out.educational_score, (int, float))
