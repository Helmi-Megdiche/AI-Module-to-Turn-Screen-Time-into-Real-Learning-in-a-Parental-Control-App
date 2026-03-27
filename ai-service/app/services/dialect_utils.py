"""
Heuristic Tunisian / Arabizi risky-term detection (post-OCR).

Digits are mapped to Arabic letters using a single canonical table. Latin fragments are
normalized only for tokens that already start with an Arabic letter after digit mapping,
to limit false positives (e.g. English words like maybe containing ayb).
Whole-token Arabizi spellings that conflict with the digit table are listed in ARABIZI_WHOLE_WORD.
"""

from __future__ import annotations

import re
import unicodedata

DIGIT_MAP: dict[str, str] = {
    "2": "أ",
    "3": "ع",
    "4": "ش",
    "5": "خ",
    "6": "ط",
    "7": "ح",
    "8": "ق",
    "9": "ص",
    "0": "و",
}

ARABIZI_WHOLE_WORD: dict[str, str] = {
    "9ahba": "قحبة",
}

LATIN_MAP: tuple[tuple[str, str], ...] = (
    ("ayb", "يب"),
    ("mar", "مار"),
)

RISKY_WORDS: frozenset[str] = frozenset(
    {
        "عيب",
        "حرام",
        "سب",
        "خايب",
        "كلامخايب",
        "حمار",
        "كلب",
        "عبد",
        "زبي",
        "كس",
        "كسم",
        "قحبة",
        "نايك",
        "منيوك",
        "طيز",
        "زق",
        "نيك",
        "شرموطة",
        "قواد",
        "قذر",
    }
)

_ARABIC_LEADING = re.compile(r"^[\u0600-\u06FF]")


def normalise_word(word: str) -> str:
    """Normalize one token for dictionary lookup (unicode, digits, minimal Latin Arabizi)."""
    w = unicodedata.normalize("NFKD", (word or "").lower())
    w = re.sub(r"[^\w]", "", w, flags=re.UNICODE)
    if not w:
        return ""
    if w in ARABIZI_WHOLE_WORD:
        return ARABIZI_WHOLE_WORD[w]
    t = w
    for digit, letter in DIGIT_MAP.items():
        t = t.replace(digit, letter)
    if _ARABIC_LEADING.match(t):
        for frag, repl in sorted(LATIN_MAP, key=lambda x: -len(x[0])):
            if frag in t:
                t = t.replace(frag, repl)
    return t


def contains_risky_dialect(text: str) -> tuple[bool, list[str]]:
    """Return (has_risk, matched_canonical_words) for tokens matching RISKY_WORDS."""
    if not (text or "").strip():
        return False, []

    words = re.findall(r"\b\w+\b", text, flags=re.UNICODE)
    matched: list[str] = []
    seen: set[str] = set()
    for w in words:
        norm = normalise_word(w)
        if norm and norm in RISKY_WORDS and norm not in seen:
            seen.add(norm)
            matched.append(norm)
    return (len(matched) > 0, matched)