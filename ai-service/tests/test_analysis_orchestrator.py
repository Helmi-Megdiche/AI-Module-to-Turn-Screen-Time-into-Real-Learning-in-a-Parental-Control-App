from app.services.analysis_orchestrator import _apply_sexual_content_safeguard


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
