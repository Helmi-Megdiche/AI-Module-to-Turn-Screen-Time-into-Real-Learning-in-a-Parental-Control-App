from app.services.ocr_text_cleanup import clean_ocr_text


def test_clean_ocr_removes_digit_heavy_tokens():
    raw = "hello m54 100k world"
    out = clean_ocr_text(raw, digit_ratio_threshold=0.5)
    assert out == "hello world"


def test_clean_ocr_keeps_mixed_arabizi():
    raw = "3asslemna hello"
    out = clean_ocr_text(raw, digit_ratio_threshold=0.5)
    assert out == "3asslemna hello"


def test_clean_ocr_empty():
    assert clean_ocr_text("", digit_ratio_threshold=0.5) == ""


def test_clean_ocr_half_digits_at_threshold_kept():
    """At default threshold, tokens that are exactly half digits stay (e.g. 80u2el)."""
    raw = "x 80u2el y"
    out = clean_ocr_text(raw, digit_ratio_threshold=0.5)
    assert out == raw
