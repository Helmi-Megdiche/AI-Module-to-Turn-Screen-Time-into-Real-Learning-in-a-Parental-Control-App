# PFE engineering roadmap and sprint tracking

This document tracks **delivery status** and **next priorities** for the AI module and related stack. Historical decisions are appended, not rewritten; status rows reflect the repository as of the last roadmap update.

---

## Feature status — Arabic OCR + Tunisian dialect risk detection

| Item | Status |
|------|--------|
| Arabic OCR + Tunisian dialect risk detection | **COMPLETED** |
| Automated tests (dialect unit tests + full `run-all-tests.js`) | **TESTED** |
| Production-hardening / long-run validation | Stable for **thesis demo** scope |
| Integrated into analyze pipeline | **INTEGRATED** (`analysis_orchestrator.py`) |

**Evidence in repo:** `ai-service/app/services/ocr_service.py`, `dialect_utils.py`, `analysis_orchestrator.py`; `ai-service/tests/test_dialect_utils.py`; root `README.md` §6.3–6.7.

---

## Sprint tracking (ESPRIT-compatible)

### Sprint AI-02 — **DONE**

| Deliverable | Status |
|-------------|--------|
| Arabic OCR integration (EasyOCR `en` / `ar`; `fr` excluded — incompatible with `ar` in same reader) | Done |
| Arabizi normalization (digits + minimal Latin + whole-token map where needed) | Done |
| Tunisian dialect moderation (lexicon + `tunisian_dialect_risk` + bounded `+0.1` text risk) | Done |
| Unit testing | Done |
| Documentation updates | Done |

---

## AI internal pipeline (reference)

Ordered stages inside `POST /analyze` (text path):

1. Screenshot in → decode image → **OCR** (EasyOCR `en` / `ar`).
2. **Text moderation** — zero-shot classification (`moderation_service`); unchanged by dialect code.
3. **Dialect normalization layer** — token normalization (`dialect_utils`); **heuristic**, **deterministic**, **low-latency** (no extra transformer call).
4. **Tunisian / Arabizi keyword detection** — dictionary match on normalized tokens.
5. **Risk adjustment** — if matches: `matchedKeywords` extended with `tunisian_dialect_risk` and canonical hits; **text** `risk_score += 0.1` capped at **1.0** (never decreases baseline moderation score).
6. **Fusion** — `max(adjusted_text_risk, vision_risk)`; keywords concatenated; category from fused risk.

**Compatibility:** Dialect logic does **not** modify `moderate()` or `ModerationResult` in place (frozen dataclass); orchestrator **copies** keywords and score, then augments. Outputs remain **deterministic** for a given OCR string and image.

---

## Key AI components (index)

| Component | File |
|-----------|------|
| OCR | `ai-service/app/services/ocr_service.py` |
| Dialect / Arabizi heuristics | `ai-service/app/services/dialect_utils.py` |
| Orchestration (moderation + dialect + vision) | `ai-service/app/services/analysis_orchestrator.py` |
| Text moderation | `ai-service/app/services/moderation_service.py` |
| Vision | `ai-service/app/services/vision_service.py` |
| HTTP API | `ai-service/app/main.py` |

---

## Next priorities — AI improvements

### Priority 1

- Context-aware moderation (sentence-level meaning beyond token dictionary).
- Multi-keyword risk weighting (non-binary aggregation).
- Semantic similarity for dialect / slang variants (reduce lexicon brittleness).

### Priority 2

- Fine-tuned classifier for Arabic and regional dialects.
- Custom embedding model for risky slang / evolving vocabulary.
- Adaptive thresholds using curated evaluation datasets.

### Priority 3

- OCR pipeline performance (caching, batching, model selection).
- **Add French OCR** via a **second** EasyOCR reader (separate from `en`+`ar`) if full French screenshot text is required.
- Batch screenshot analysis API (if product needs throughput).
- Confidence calibration between vision and text risk (fused score interpretability).

---

## Changelog (roadmap file only)

| Date | Note |
|------|------|
| 2026-03 | Marked Sprint AI-02 and Arabic OCR + dialect feature **completed** after integration and test validation. Added next-priority backlog. |
