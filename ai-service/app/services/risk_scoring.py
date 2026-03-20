"""Keyword-based risk score and category (no ML classifier — keeps the demo predictable)."""

from __future__ import annotations

import re

# Lists from product spec — tune these if parents want stricter/looser rules
VIOLENCE = ["kill", "fight", "blood", "attack"]
TOXIC = ["hate", "stupid", "idiot", "loser"]
DANGEROUS = ["challenge", "jump", "fire", "knife"]

ALL_KEYWORDS = VIOLENCE + TOXIC + DANGEROUS


def _levenshtein(a: str, b: str) -> int:
    """Classic edit distance — small strings only, fine for our keyword lengths."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        cur = [i + 1]
        for j, cb in enumerate(b):
            ins = cur[j] + 1
            delete = prev[j + 1] + 1
            sub = prev[j] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def _max_edits_allowed(keyword: str) -> int:
    """OCR often swaps 1–2 characters on short words (e.g. loser → leser)."""
    n = len(keyword)
    if n <= 3:
        return 0
    if n <= 6:
        return 1
    return 2


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _keyword_hit_in_text(lowered: str, kw: str) -> bool:
    if kw in lowered:
        return True

    max_ed = _max_edits_allowed(kw)
    if max_ed == 0:
        return False

    for token in _tokens(lowered):
        if abs(len(token) - len(kw)) > max_ed:
            continue
        if _levenshtein(token, kw) <= max_ed:
            return True
    return False


def _canonical_for_token(token_lower: str) -> str | None:
    """Map one OCR token to the canonical list word we matched (first list hit wins)."""
    for kw in ALL_KEYWORDS:
        if token_lower == kw:
            return kw
        max_ed = _max_edits_allowed(kw)
        if max_ed == 0:
            continue
        if abs(len(token_lower) - len(kw)) > max_ed:
            continue
        if _levenshtein(token_lower, kw) <= max_ed:
            return kw
    return None


def matched_keywords(text: str) -> list[str]:
    """Canonical keywords that fired (substring or fuzzy), stable order as in ALL_KEYWORDS."""
    if not text or not text.strip():
        return []
    lowered = text.lower()
    out: list[str] = []
    for kw in ALL_KEYWORDS:
        if _keyword_hit_in_text(lowered, kw):
            out.append(kw)
    return out


def build_display_text(raw: str) -> str:
    """
    Parent-friendly line: same as OCR but tokens replaced by canonical keywords when we fuzzy-matched.
    Raw `text` stays untouched in the API for audit; this is what you show in the parent UI.
    """
    if not raw:
        return ""

    def replace_word(m: re.Match[str]) -> str:
        word = m.group(0)
        tl = word.lower()
        canon = _canonical_for_token(tl)
        if canon is None:
            return word
        # Preserve original casing style roughly: if all-caps, uppercase canon; else use canonical lower
        if word.isupper():
            return canon.upper()
        if word[0].isupper():
            return canon.capitalize()
        return canon

    return re.sub(r"[A-Za-z0-9]+", replace_word, raw)


def count_keyword_hits(text: str) -> int:
    return len(matched_keywords(text))


def compute_risk_score(match_count: int) -> float:
    """Map hit count to [0, 1]. Four distinct hits already maxes out — keeps single-word screens meaningful."""
    if match_count <= 0:
        return 0.0
    return min(1.0, match_count * 0.25)


def category_from_score(risk_score: float) -> str:
    if risk_score < 0.25:
        return "safe"
    if risk_score < 0.65:
        return "risky"
    return "dangerous"
