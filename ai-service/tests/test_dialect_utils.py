from app.services.dialect_utils import (
    contains_risky_dialect,
    normalise_word,
    risky_arabic_effective,
)


def test_digit_normalisation():
    assert normalise_word("3ayb") == "عيب"


def test_detect_arabizi():
    found, words = contains_risky_dialect("this is 3ayb")
    assert found is True
    assert "عيب" in words


def test_detect_arabic():
    found, words = contains_risky_dialect("هذا عيب")
    assert found is True


def test_safe_text():
    found, words = contains_risky_dialect("hello world")
    assert found is False
    assert words == []


def test_empty():
    found, words = contains_risky_dialect("")
    assert found is False
    assert words == []


def test_arabizi_7mar():
    assert normalise_word("7mar") == "حمار"


def test_arabizi_9ahba():
    assert normalise_word("9ahba") == "قحبة"


def test_json_exact_latin_kalb():
    """Latin key from tunisian_dialect.json (no Arabizi digits)."""
    found, words = contains_risky_dialect("you kalb")
    assert found is True
    assert "كلب" in words


def test_fuzzy_latin_typo():
    """difflib recovery for minor typo vs JSON key."""
    found, words = contains_risky_dialect("typo 3aybb here")
    assert found is True
    assert "عيب" in words


def test_risky_arabic_includes_baseline():
    assert "عيب" in risky_arabic_effective()
