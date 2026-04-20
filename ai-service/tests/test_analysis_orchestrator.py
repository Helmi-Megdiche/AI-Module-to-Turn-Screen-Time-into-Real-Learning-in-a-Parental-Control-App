from __future__ import annotations

import pytest

import app.services.analysis_orchestrator as orch
from app.services.analysis_orchestrator import (
    _apply_sexual_content_safeguard,
    build_analyze_response_from_plain_text,
)
from app.services.moderation_service import ModerationResult


def test_safeguard_does_nothing_for_other_keywords():
    risk, kw = _apply_sexual_content_safeguard(0.95, ["violence"])
    assert risk == 0.95
    assert kw == ["violence"]


def test_safeguard_caps_when_only_sexual_content():
    risk, kw = _apply_sexual_content_safeguard(0.95, ["sexual content"])
    assert risk == 0.6
    assert kw == ["sexual content"]


def test_safeguard_does_nothing_when_risk_already_low():
    risk, kw = _apply_sexual_content_safeguard(0.8, ["sexual content"])
    assert risk == 0.8
    assert kw == ["sexual content"]


def test_safeguard_does_nothing_for_multiple_keywords():
    risk, kw = _apply_sexual_content_safeguard(0.95, ["sexual content", "violence"])
    assert risk == 0.95
    assert kw == ["sexual content", "violence"]


def _fake_moderate_factory(risk_score: float) -> callable:
    def _fake_moderate(_text: str) -> ModerationResult:
        return ModerationResult(
            matched_keywords=[],
            risk_score=risk_score,
            category="safe",
            display_text="",
            label_scores={},
            inference_ms=0.0,
            used_fallback=False,
            educational_score=0.0,
        )

    return _fake_moderate


def test_french_grooming_sets_risky_label_and_floor(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(orch, "moderate", _fake_moderate_factory(0.0))
    out = build_analyze_response_from_plain_text("viens chez moi, c'est notre secret", image=None)
    assert out.category == "risky"
    assert out.risk_score >= 0.75
    assert "french_grooming_pattern" in out.matched_keywords


def test_french_dangerous_sets_dangerous_label_and_floor(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(orch, "moderate", _fake_moderate_factory(0.0))
    out = build_analyze_response_from_plain_text("je vais te tuer si tu parles", image=None)
    assert out.category == "dangerous"
    assert out.risk_score >= 0.92
    assert "french_dangerous_pattern" in out.matched_keywords


def test_french_dangerous_priority_over_grooming(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(orch, "moderate", _fake_moderate_factory(0.0))
    text = "je vais te tuer et ensuite viens chez moi c'est notre secret"
    out = build_analyze_response_from_plain_text(text, image=None)
    assert out.category == "dangerous"
    assert out.risk_score >= 0.92
    assert "french_dangerous_pattern" in out.matched_keywords
    assert "french_grooming_pattern" not in out.matched_keywords


def test_french_grooming_not_triggered_for_benign_french(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(orch, "moderate", _fake_moderate_factory(0.0))
    out = build_analyze_response_from_plain_text("viens à l'école demain", image=None)
    assert "french_grooming_pattern" not in out.matched_keywords
    assert "french_dangerous_pattern" not in out.matched_keywords


def test_arabizi_threat_regression_reaches_dangerous_band(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(orch, "moderate", _fake_moderate_factory(0.82))
    out = build_analyze_response_from_plain_text("ndhba7ek", image=None)
    assert "tunisian_dialect_risk" in out.matched_keywords
    assert out.risk_score >= 0.9
    assert out.category == "dangerous"
