from app.services.ocr_text_cleanup import clean_ocr_text, should_keep_token


def test_clean_ocr_removes_digit_heavy_tokens():
    raw = "hello m54 100k world"
    out = clean_ocr_text(raw, digit_ratio_threshold=0.4)
    assert out == "hello world"


def test_clean_ocr_keeps_mixed_arabizi():
    raw = "3asslemna hello"
    out = clean_ocr_text(raw, digit_ratio_threshold=0.4)
    assert out == "3asslemna hello"


def test_clean_ocr_keeps_pure_digit_token():
    raw = "call 123456 here"
    out = clean_ocr_text(raw, digit_ratio_threshold=0.4)
    assert out == raw


def test_clean_ocr_empty():
    assert clean_ocr_text("", digit_ratio_threshold=0.4) == ""


def test_clean_ocr_drops_half_digit_mixed_at_default_threshold():
    """Mixed tokens like 80u2el exceed 0.4 digit ratio and are removed."""
    raw = "x 80u2el y"
    out = clean_ocr_text(raw, digit_ratio_threshold=0.4)
    assert out == "x y"


def test_should_keep_token_drops_short_digit_mixed():
    assert should_keep_token("5dhit5") is False
    assert should_keep_token("80u2el") is False
    assert should_keep_token("3ayb") is True
    assert should_keep_token("12345") is True
    assert should_keep_token("longer80mix") is True
