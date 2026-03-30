"""Light OCR post-processing before text moderation (no heavy dependencies)."""


def should_keep_token(word: str) -> bool:
    """
    Keep token unless it is short (≤5 chars) and contains digits but is not pure digits.

    This removes noisy OCR tokens like ``5dhit5`` while preserving dialect words like ``3ayb``.
    """
    if len(word) > 5:
        return True
    if word.isdigit():
        return True
    if any(c.isdigit() for c in word):
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
