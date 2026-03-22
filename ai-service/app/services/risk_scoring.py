"""
Rule-based **fallback** risk scoring when the transformer is unavailable or OCR is unusable.

Each ``SignalRule`` combines:

- **aliases** — vocabulary that can match OCR tokens (with fuzzy edit distance),
- optional **context** words that must appear nearby,
- optional **regex patterns** for high-precision phrases,
- a **weight** folded into ``compute_risk_score``.

This module stays **deterministic** (no network) so demos and unit tests are reproducible.
The coarse ``category_from_score`` thresholds here differ from ``config.py`` — the HTTP API uses
``moderation_service.category_from_model_score`` for the final label.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re


@dataclass(frozen=True)
class SignalRule:
    """One interpretable risk signal (e.g. self-harm, hate speech) with matching logic."""

    label: str
    weight: float
    aliases: tuple[str, ...] = ()
    context: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()
    window: int = 3


@dataclass(frozen=True)
class RiskAnalysis:
    """Lightweight result type shared with ``moderation_service.analyze_text``."""

    matched_keywords: list[str]
    risk_score: float
    display_text: str


# Ordered list of rules evaluated independently; multiple can fire on one string.
SIGNAL_RULES: tuple[SignalRule, ...] = (
    SignalRule(
        label="self-harm",
        weight=1.2,
        aliases=("harm", "suicide", "cut", "cutting"),
        context=("self", "yourself", "deliberate", "intentional", "damage", "injury", "attempt", "void"),
        patterns=(
            r"\bkill\s+yourself\b",
            r"\bkill\s+myself\b",
            r"\bhurt\s+yourself\b",
            r"\bhurt\s+myself\b",
            r"\bcut\s+yourself\b",
            r"\bcut\s+myself\b",
            r"\bend\s+your\s+life\b",
            r"\bend\s+my\s+life\b",
            r"\bsuicide\b",
            r"\bself[\s-]*harm[a-z]{0,2}\b",
        ),
        window=2,
    ),
    SignalRule(
        label="violent threat",
        weight=0.95,
        aliases=("kill", "stab", "shoot", "attack", "beat"),
        context=("you", "him", "her", "them", "teacher", "kid", "child", "mom", "dad"),
        patterns=(
            r"\bi(?:'ll| will| am going to|m gonna)?\s+(?:kill|stab|shoot)\s+(?:you|him|her|them)\b",
            r"\b(?:kill|stab|shoot)\s+(?:you|him|her|them)\b",
            r"\bbeat\s+(?:you|him|her|them)\b",
        ),
    ),
    SignalRule(
        label="weapon",
        weight=0.55,
        aliases=("knife", "gun", "pistol", "rifle", "bullet", "weapon"),
    ),
    SignalRule(
        label="dangerous jump",
        weight=0.75,
        aliases=("jump", "climb"),
        context=("roof", "bridge", "window", "balcony", "building", "ledge", "high", "train", "moving"),
        patterns=(
            r"\bjump\s+off\b",
            r"\bclimb\s+(?:onto|up)\b",
        ),
    ),
    SignalRule(
        label="dangerous fire",
        weight=0.6,
        aliases=("fire", "burn", "lighter", "gasoline", "petrol"),
        context=("set", "house", "room", "bed", "school", "inside", "challenge", "spray", "bottle"),
        patterns=(
            r"\bset\s+(?:it|this|the\s+\w+)?\s*on\s+fire\b",
            r"\bplay(?:ing)?\s+with\s+fire\b",
            r"\bburn\s+(?:the|my|your|his|her)\b",
        ),
    ),
    SignalRule(
        label="poison or overdose",
        weight=0.85,
        aliases=("bleach", "poison", "overdose", "pill", "pills"),
        patterns=(
            r"\bdrink\s+bleach\b",
            r"\btake\s+\d+\s+pills?\b",
            r"\boverdose\b",
        ),
    ),
    SignalRule(
        label="dangerous challenge",
        weight=0.65,
        aliases=("challenge", "trend"),
        context=("knife", "fire", "burn", "jump", "balcony", "roof", "bleach", "choke", "pills", "overdose", "train"),
        patterns=(
            r"\b(?:tiktok|viral)\s+challenge\b",
        ),
    ),
    SignalRule(
        label="violent injury",
        weight=0.45,
        aliases=("blood", "bleeding", "fight"),
        patterns=(
            r"\bbeat\s+up\b",
            r"\bfight(?:ing)?\b",
        ),
    ),
    SignalRule(
        label="toxic abuse",
        weight=0.25,
        aliases=("hate", "stupid", "idiot", "loser", "worthless"),
    ),
    SignalRule(
        label="hate speech",
        weight=1.2,
        aliases=(
            "arabes",
            "arabs",
            "immigre",
            "immigres",
            "immigrant",
            "immigrants",
            "rats",
            "terrorist",
            "terrorists",
        ),
        patterns=(
            r"\bgo\s+back\s+to\s+their\s+country\b",
            r"\bi\s+hate\s+them\s+all\b",
            r"\barab(?:es|s)?\s+(?:are|is|sont)\s+terror(?:ist|ists|iste|istes)\b",
            r"\b(?:les\s+)?immigr(?:e|es|ants?)\s+sont\s+des\s+rats\b",
            r"\b(?:these|those)\s+(?:people|immigr(?:e|es|ants?)|arab(?:es|s)?)\s+are\s+(?:rats|vermin|terrorists?)\b",
            r"\b(?:hate|deteste)\s+(?:them|les)\s+(?:all|tous)\b",
        ),
    ),
)

ALL_KEYWORDS = [
    alias
    for rule in SIGNAL_RULES
    for alias in rule.aliases
]


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
    """Allow OCR fuzziness, but stay strict on very short words to avoid false positives."""
    n = len(keyword)
    if n <= 4:
        return 0
    if n <= 6:
        return 1
    return 2


def _tokens(text: str) -> list[str]:
    """Lowercase alphanumeric tokens — basis for fuzzy keyword search."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _token_matches_keyword(token_lower: str, kw: str) -> bool:
    """Exact match or small Levenshtein distance for OCR typos."""
    if token_lower == kw:
        return True

    max_ed = _max_edits_allowed(kw)
    if max_ed == 0 or abs(len(token_lower) - len(kw)) > max_ed:
        return False
    return _levenshtein(token_lower, kw) <= max_ed


def _keyword_hit_in_text(lowered: str, kw: str) -> bool:
    """Substring or fuzzy token hit — helper for rare call sites."""
    if kw in lowered:
        return True
    return any(_token_matches_keyword(token, kw) for token in _tokens(lowered))


def _match_indexes(tokens: list[str], candidates: tuple[str, ...]) -> list[int]:
    """Indices of tokens that fuzzy-match any candidate keyword."""
    if not candidates:
        return []
    out: list[int] = []
    for i, token in enumerate(tokens):
        if any(_token_matches_keyword(token, candidate) for candidate in candidates):
            out.append(i)
    return out


def _has_context_nearby(tokens: list[str], anchors: tuple[str, ...], context: tuple[str, ...], window: int) -> bool:
    """True when an anchor token and a context token appear within ``window`` tokens of each other."""
    anchor_indexes = _match_indexes(tokens, anchors)
    if not anchor_indexes:
        return False
    context_indexes = _match_indexes(tokens, context)
    if not context_indexes:
        return False
    return any(abs(a - c) <= window for a in anchor_indexes for c in context_indexes)


def _rule_matches(lowered: str, tokens: list[str], rule: SignalRule) -> bool:
    """Dispatch: regex win > alias-only > alias+context proximity."""
    if any(re.search(pattern, lowered) for pattern in rule.patterns):
        return True
    if rule.aliases and not rule.context and _match_indexes(tokens, rule.aliases):
        return True
    if rule.aliases and rule.context and _has_context_nearby(tokens, rule.aliases, rule.context, rule.window):
        return True
    return False


def _canonical_for_token(token_lower: str) -> str | None:
    """Map one OCR token to the canonical list word we matched (first list hit wins)."""
    for kw in ALL_KEYWORDS:
        if _token_matches_keyword(token_lower, kw):
            return kw
    return None


def _matched_labels_and_weights(lowered: str, tokens: list[str]) -> tuple[list[str], list[float]]:
    """Labels that fired and their weights, in ``SIGNAL_RULES`` order."""
    matches = [rule.label for rule in SIGNAL_RULES if _rule_matches(lowered, tokens, rule)]
    weights = [rule.weight for rule in SIGNAL_RULES if rule.label in matches]
    return matches, weights


def _format_canonical_casing(original_word: str, canonical: str) -> str:
    """Preserve rough casing when swapping OCR tokens for canonical keywords."""
    if original_word.isupper():
        return canonical.upper()
    if original_word[0].isupper():
        return canonical.capitalize()
    return canonical


def _replace_token_for_display(m: re.Match[str]) -> str:
    """Regex callback: one alphanumeric token → canonical keyword if fuzzy-matched."""
    word = m.group(0)
    tl = word.lower()
    canon = _canonical_for_token(tl)
    if canon is None:
        return word
    return _format_canonical_casing(word, canon)


def analyze_text(text: str) -> RiskAnalysis:
    """Run all rules, aggregate weights into a risk score, build parent-facing ``display_text``."""
    if not text or not text.strip():
        return RiskAnalysis(matched_keywords=[], risk_score=0.0, display_text="")

    lowered = text.lower()
    tokens = _tokens(lowered)
    matches, weights = _matched_labels_and_weights(lowered, tokens)
    risk_score = compute_risk_score(weights, matches)
    return RiskAnalysis(
        matched_keywords=matches,
        risk_score=risk_score,
        display_text=build_display_text(text),
    )


def matched_keywords(text: str) -> list[str]:
    """Matched risk signals in stable order, not just isolated words."""
    return analyze_text(text).matched_keywords


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
    """Convenience counter — not used on the hot HTTP path."""
    return len(matched_keywords(text))


def compute_risk_score(weights: list[float], labels: list[str] | None = None) -> float:
    """
    Turn weighted signals into a bounded score.

    We use a smooth curve so one minor insult stays low, while multiple severe
    signals rapidly approach the dangerous range.
    """
    if not weights:
        return 0.0

    raw_score = sum(weights)
    score = 1 - math.exp(-raw_score)

    labels = labels or []
    if "dangerous challenge" in labels and any(
        label in labels for label in ("weapon", "dangerous fire", "dangerous jump", "poison or overdose")
    ):
        score += 0.12
    if "violent threat" in labels and "weapon" in labels:
        score += 0.08

    return round(min(1.0, score), 2)


def category_from_score(risk_score: float) -> str:
    """Legacy three-band label for **rule-only** scores (not the same thresholds as ``config.py``)."""
    if risk_score < 0.25:
        return "safe"
    if risk_score < 0.65:
        return "risky"
    return "dangerous"
