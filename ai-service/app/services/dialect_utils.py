"""
Heuristic Tunisian / Arabizi risky-term detection (post-OCR).

Digits are mapped to Arabic letters using a single canonical table. Yamli-style Latin
substrings are applied only when the token contains an Arabizi digit, to avoid mangling
English (e.g. ``school``). Latin fragments are normalized only when the token already
starts with an Arabic letter after digit mapping.

Risky Latin spellings load from ``ai-service/data/tunisian_dialect.json`` (lazy, once).
Arabic risk set = in-code ``RISKY_WORDS`` ∪ JSON ``arabic`` values. ``difflib`` fuzzy
matching recovers minor OCR/Latin typos against JSON keys.
"""

from __future__ import annotations

import difflib
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, Final

logger = logging.getLogger(__name__)

_DIALECT_JSON: Final[Path] = (
    Path(__file__).resolve().parent.parent.parent / "data" / "tunisian_dialect.json"
)

_DIALECT_CACHE: dict[str, Any] | None = None

FUZZY_LATIN_CUTOFF: Final[float] = 0.8

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

# Longest keys first (applied only when token has an Arabizi digit — see ``_apply_pattern_map``).
PATTERN_MAP: tuple[tuple[str, str], ...] = tuple(
    sorted(
        (
            ("gh", "غ"),
            ("ch", "ش"),
            ("sh", "ش"),
            ("kh", "خ"),
            ("th", "ث"),
            ("dh", "ذ"),
            ("ou", "و"),
            ("oo", "و"),
            ("ee", "ي"),
            ("ai", "اي"),
            ("aa", "ا"),
        ),
        key=lambda x: -len(x[0]),
    )
)

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


def _word_has_arabizi_digit(word: str) -> bool:
    return any(c in DIGIT_MAP for c in word)


def _apply_pattern_map(t: str, original_word: str) -> str:
    if not _word_has_arabizi_digit(original_word):
        return t
    for pat, repl in PATTERN_MAP:
        t = t.replace(pat, repl)
    return t


def _load_dialect_bundle() -> dict[str, Any]:
    global _DIALECT_CACHE
    if _DIALECT_CACHE is not None:
        return _DIALECT_CACHE

    latin_to_arabic: dict[str, str] = {}
    json_arabic: set[str] = set()
    try:
        data = json.loads(_DIALECT_JSON.read_text(encoding="utf-8"))
        for item in data:
            lat = str(item["latin"]).lower()
            arb = str(item["arabic"])
            latin_to_arabic[lat] = arb
            json_arabic.add(arb)
    except FileNotFoundError:
        logger.warning("tunisian_dialect.json not found at %s", _DIALECT_JSON)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Failed to parse tunisian_dialect.json: %s", e)

    risky_arabic_effective: frozenset[str] = frozenset(RISKY_WORDS) | frozenset(json_arabic)
    _DIALECT_CACHE = {
        "latin_to_arabic": latin_to_arabic,
        "risky_arabic_effective": risky_arabic_effective,
        "latin_keys": sorted(latin_to_arabic.keys()),
    }
    return _DIALECT_CACHE


def risky_arabic_effective() -> frozenset[str]:
    """Effective Arabic risk lexicon (static ∪ JSON). Exposed for tests."""
    return _load_dialect_bundle()["risky_arabic_effective"]


def _fuzzy_latin_key(word_lower: str, latin_keys: list[str]) -> str | None:
    matches = difflib.get_close_matches(
        word_lower, latin_keys, n=1, cutoff=FUZZY_LATIN_CUTOFF
    )
    return matches[0] if matches else None


def normalise_word(word: str) -> str:
    """Normalize one token for dictionary lookup (unicode, digits, Yamli patterns, Latin Arabizi)."""
    w = unicodedata.normalize("NFKD", (word or "").lower())
    w = re.sub(r"[^\w]", "", w, flags=re.UNICODE)
    if not w:
        return ""
    if w in ARABIZI_WHOLE_WORD:
        return ARABIZI_WHOLE_WORD[w]
    t = w
    for digit, letter in DIGIT_MAP.items():
        t = t.replace(digit, letter)
    t = _apply_pattern_map(t, w)
    if _ARABIC_LEADING.match(t):
        for frag, repl in sorted(LATIN_MAP, key=lambda x: -len(x[0])):
            if frag in t:
                t = t.replace(frag, repl)
    return t


def contains_risky_dialect(text: str) -> tuple[bool, list[str]]:
    """Return (has_risk, matched_canonical Arabic words) using JSON + normalization + fuzzy Latin."""
    if not (text or "").strip():
        return False, []

    bundle = _load_dialect_bundle()
    latin_to_arabic: dict[str, str] = bundle["latin_to_arabic"]
    risky: frozenset[str] = bundle["risky_arabic_effective"]
    latin_keys: list[str] = bundle["latin_keys"]

    words = re.findall(r"\b\w+\b", text, flags=re.UNICODE)
    matched: list[str] = []
    seen: set[str] = set()
    for w in words:
        lower = w.lower()
        canonical: str | None = None

        if lower in latin_to_arabic:
            canonical = latin_to_arabic[lower]
        else:
            norm = normalise_word(w)
            if norm in risky:
                canonical = norm
            else:
                fuzz = _fuzzy_latin_key(lower, latin_keys)
                if fuzz is not None:
                    canonical = latin_to_arabic.get(fuzz)

        if canonical and canonical in risky and canonical not in seen:
            seen.add(canonical)
            matched.append(canonical)
    return (len(matched) > 0, matched)
