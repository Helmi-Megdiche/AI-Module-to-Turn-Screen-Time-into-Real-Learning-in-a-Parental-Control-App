# Test run report — PFE parental-control stack

**Date:** 2026-03-21  
**Environment:** Windows, Cursor worktree `sez`  
**Python:** `AI_VENV_PYTHON` → OneDrive `ai-service\.venv\Scripts\python.exe` (when set)  
**Command:** `node scripts/run-all-tests.js --full`  
**Overall result:** **PASS** (exit code 0)

---

## 1. Backend — Jest

| Metric | Value |
|--------|--------|
| Test suites | 2 passed |
| Tests | **6 passed** |
| Time | ~0.48 s |

**Suites**

- `src/services/__tests__/aiService.test.js` — `analyzeImage`: default URL/timeout, env overrides, axios error wrapping.
- `src/services/__tests__/analyzeService.test.js` — `missionForRiskScore`: bands `<0.3` (2 pts), `0.3–0.7` (5 pts), `>0.7` (10 pts).

---

## 2. AI service — pytest

| Metric | Value |
|--------|--------|
| Tests | **8 passed** |
| Time | ~4.4 s |

**Notes:** Deprecation warnings from EasyOCR/SWIG bindings (`SwigPyPacked`, etc.) — environmental, not test failures.

**Coverage (high level):** `moderate()` empty text, whitespace-only, short text, classifier-not-ready path, mocked zero-shot scores (dangerous / risky bands), inference exception → fallback, length-at-threshold behaviour.

---

## 3. AI service — offline moderation evaluation

**Script:** `evaluate_moderation.py --strict`  
**Model:** `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` (CPU)  
**Cases:** 15 (`moderation_eval_dataset.json`)

### Strict gate (must pass for CI)

- All **fallback** flags match expectations: **15 / 15**
- Flagship case **`danger-fr-en-hate-mixed`:** `category=dangerous`, `risk=0.98`, **`hate speech`** present in labels, fallback **not** used → **PASS**

### Summary metrics

| Metric | Value |
|--------|--------|
| category_ok | 11 / 15 |
| risk_range_ok | 12 / 15 |
| fallback_ok | 15 / 15 |
| label_exact | 4 / 15 |
| avg_inference_ms | 2442.37 |
| p95_inference_ms | 2876.11 |

### Cases with category or risk-band mismatch (informational)

These do **not** fail `--strict` unless flagship or fallback breaks:

- `risky-en-harassment` — predicted **dangerous** (risk 0.97); model conservative vs “risky” expectation.
- `risky-fr-bullying` — **dangerous** (0.93).
- `risky-en-sexual` — **safe** (0.02) vs expected risky.
- `ocr-noisy-threat` — **dangerous** vs expected risky (risk in range OK).

Known design choice: `DANGEROUS_THRESHOLD=0.85` still allows many harassment-like strings to score ≥0.85.

---

## 4. Conclusion

- **Automated unit/integration-style tests:** all green.  
- **Regression gate (`--strict`):** green; flagship hate-speech case and all fallback expectations satisfied.  
- **Dataset alignment:** 11/15 category and 12/15 risk-range matches — acceptable for current calibration; document in thesis as model/dataset tension.

---

*Paste this file or the sections above into ChatGPT for context.*
