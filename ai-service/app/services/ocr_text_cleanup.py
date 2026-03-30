"""Light OCR post-processing before text moderation (no heavy dependencies)."""


def should_keep_token(word: str) -> bool:
    """
    Drop **short** tokens that look like OCR junk: **two or more** digit characters in a
    mixed alphanumeric word (e.g. ``5dhit5``, ``80u2el``).

    **Single-digit** Arabizi spellings (``3``→ع, ``9``→ق, etc.) are preserved: ``3ayb``,
    ``9ahba``, ``7mar`` stay.
    """
    if len(word) > 6:
        return True
    if word.isdigit():
        return True
    digit_count = sum(1 for c in word if c.isdigit())
    if digit_count >= 2:
        return False
    return True


def clean_ocr_text(text: str, digit_ratio_threshold: float = 0.4) -> str:
    """
    Remove whitespace-separated tokens whose digit/total character ratio is too high.

    Garbled OCR often yields digit-heavy pseudo-words that confuse zero-shot NLI moderation.
    Tokens are kept when either:

    - the token is **all digits** (e.g. long numeric codes), or
    - ``digit_count/len(word) <= digit_ratio_threshold``.
    """
    if not text:
        return text

    words = text.split()
    cleaned: list[str] = []
    for word in words:
        if not word:
            continue
        digit_count = sum(1 for c in word if c.isdigit())
        if digit_count == len(word) or digit_count / len(word) <= digit_ratio_threshold:
            cleaned.append(word)
    return " ".join(cleaned)
