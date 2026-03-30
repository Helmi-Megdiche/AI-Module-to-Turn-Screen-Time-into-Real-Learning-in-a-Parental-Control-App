# PFE Engineering Roadmap and Sprint Tracking (Updated)

This roadmap reflects the **current implemented state** of the project and defines the next 6-month PFE execution plan without changing core architecture or API contracts.

Project goal: an AI-powered parental control system that transforms screen time into educational missions.

---

## 1) Current State Snapshot

### Core pipeline maturity

| Layer | Status | Notes |
|---|---|---|
| OCR (English + Arabic) | Stable | EasyOCR `en + ar` integrated |
| Tunisian dialect detection | Stable | Heuristic normalization + lexicon |
| Zero-shot moderation | Stable | Multilingual classification |
| Vision risk detection | Stable | NSFW model integrated |
| Risk fusion logic | Stable | `max(text, vision)` |
| Mission generation | Stable | Rule-based personalization |
| Exposure frequency logic | Stable | Window based (`1h`, `24h`, `7d`) |
| Parent dashboard endpoints | Implemented | Aggregation endpoints available |
| Flutter capture pipeline | Stable | MediaProjection resilience in place |
| Automated tests | Passing | Jest + pytest + cross-stack |
| Explainability packaging | Partial | Keywords exist, structured layer missing |
| AI evaluation benchmarking | Missing | Primary weakness |
| Demo reliability layer | Partial | Not standardized |

### Feature status (AI core)

- [x] Arabic OCR + Tunisian dialect risk detection
- [x] Automated dialect tests
- [x] Analyze pipeline integration
- [x] Risk fusion orchestration
- [x] Educational content detection
- [x] Mission generation logic
- [x] Exposure frequency logic
- [x] Parent dashboard endpoints
- [ ] Structured explainability metadata layer
- [ ] AI evaluation dataset and benchmark tooling
- [ ] Standardized demo reliability tooling

---

## 2) Weakness Confirmation

Primary weakness: **AI evaluation and evidence quality**.

Main jury risk: **insufficient quantitative validation** across multilingual and noisy OCR scenarios.

What is needed (without architecture rewrite):

1. standardized offline benchmark datasets,
2. structured explainability metadata for trust,
3. reproducible evaluation artifacts,
4. reliable demo execution workflow.

---

## 3) Priority Stack (PFE Constraints)

1. **Evaluation credibility**
2. **Explainability clarity (jury + parents)**
3. **Multilingual robustness evidence**
4. **Personalization intelligence validation**
5. **Demo reliability**

Constraints preserved:

- no replacement of EasyOCR,
- no moderation model-family switch,
- no zero-shot removal,
- no dialect layer removal,
- no database/schema rewrite,
- no heavy training pipeline introduction.

---

## 4) Revised 6-Sprint Roadmap (6 Months)

## Sprint AI-03 (Month 1): Evaluation Baseline

### Deliverables checklist

- [ ] Build benchmark dataset v1 with slices:
  - English
  - Arabic
  - Arabizi/Tunisian
  - mixed-language
  - educational-safe
  - risky-harmful
  - OCR-noisy samples
- [ ] Implement evaluation scripts for:
  - precision
  - recall
  - F1
  - false-positive rate
  - false-negative rate
- [ ] Generate confusion matrix utility
- [ ] Publish baseline report artifact

### Suggested artifact paths

- `evaluation/datasets/benchmark_v1.json`
- `evaluation/scripts/*`
- `reports/baseline_metrics.md`

### Acceptance criteria

- [ ] Benchmark dataset is versioned and reproducible.
- [ ] Evaluation scripts run in one command and produce metrics + confusion matrix.
- [ ] Baseline report committed with KPI table and slice-level breakdown.

---

## Sprint AI-04 (Month 2): Explainability Trust Layer

### Deliverables checklist

- [ ] Add structured, **non-breaking optional** explainability metadata in AI output:
  - `reasonCodes` (e.g., `dialect_triggered`, `vision_dominant`, `educational_override`, `ocr_low_confidence`)
  - score decomposition fields (`textRisk`, `visionRisk`, `educationalScore`, `dialectAdjustment`)
- [ ] Add parent/jury-facing explanation cards in demo/dashboard
- [ ] Document explainability field semantics

### Acceptance criteria

- [ ] Existing clients remain compatible (no required-field break).
- [ ] At least 90% of benchmark samples include meaningful explainability metadata.
- [ ] Demo shows human-readable "why" for representative risky and educational cases.

---

## Sprint AI-05 (Month 3): Multilingual Robustness Validation

### Deliverables checklist

- [ ] Build hard-case robustness subset:
  - Arabizi digit substitutions
  - mixed Arabic-English strings
  - OCR-corrupted tokens
  - slang variations
- [ ] Add targeted regression tests for discovered failure patterns
- [ ] Establish dialect lexicon governance process (versioning + review notes)

### Acceptance criteria

- [ ] Hard-case subset is integrated into benchmark pipeline.
- [ ] Regression tests prevent re-introduction of fixed failure patterns.
- [ ] Report includes before/after metrics for multilingual hard cases.

---

## Sprint AI-06 (Month 4): Personalization Validation

### Deliverables checklist

- [ ] Implement offline mission replay evaluation workflow
- [ ] Track personalization metrics:
  - mission completion rate
  - mission success rate
  - difficulty mismatch proxy
- [ ] Apply minor tuning to rule weights/tie-breakers (no architecture change)
- [ ] Add metadata for "why this mission was selected"

### Acceptance criteria

- [ ] Replay pipeline runs on historical/seeded mission outcomes.
- [ ] At least one measurable improvement is documented vs baseline policy.
- [ ] Mission selection explanations are visible in demo for selected scenarios.

---

## Sprint AI-07 (Month 5): Reliability and Alert Flow

### Deliverables checklist

- [ ] Add demo preflight checker script
- [ ] Verify health and readiness:
  - DB connectivity
  - AI service readiness
  - seed data presence
  - mission generation sanity
- [ ] Add lightweight parent alert flow using existing exposure-frequency logic
  - threshold triggers
  - summary alerts in parent dashboard context
- [ ] Prepare deterministic seeded demo scenarios

### Acceptance criteria

- [ ] Preflight script provides pass/fail report with actionable errors.
- [ ] Demo "golden path" succeeds repeatedly on seeded setup.
- [ ] Alert trigger behavior is documented and testable.

---

## Sprint AI-08 (Month 6): Final Validation and Defense Packaging

### Deliverables checklist

- [ ] Final benchmark report: baseline vs improved metrics
- [ ] Methodology write-up for scientific defense
- [ ] Curated explainability casebook
- [ ] Final demo scenario scripts:
  - educational screenshot
  - dialect-risk chat
  - high exposure pattern
  - adaptive mission example
- [ ] Limitations and future-work section

### Acceptance criteria

- [ ] Final report includes KPI deltas and confidence narrative.
- [ ] Demo script can be executed end-to-end with reproducible outcomes.
- [ ] Jury package includes architecture consistency, evidence, and limitations.

---

## 5) Expected Measurable Improvements

- Quantified moderation quality (precision/recall/F1, FP/FN by slice)
- Better robustness evidence on noisy OCR and mixed-language cases
- Clear explainability coverage and decision traceability
- Data-backed personalization improvements
- Reduced demo failure risk via preflight and deterministic scenarios

---

## 6) Core Scope vs Stretch Goals

### Core scope (must deliver in PFE window)

- Benchmark dataset + metrics pipeline
- Explainability metadata + UI presentation
- Multilingual robustness validation
- Personalization replay evaluation
- Demo preflight + reliability process
- Final defense package with quantitative evidence

### Stretch goals (post-core, if time allows)

- Fine-tuned dialect classifier
- Slang-evolution embedding model
- Fully adaptive learning personalization
- Large-scale annotation pipeline
- Real-time push notification infrastructure

---

## 7) Sprint Progress Tracker

Use this section during execution.

- [ ] AI-03 complete
- [ ] AI-04 complete
- [ ] AI-05 complete
- [ ] AI-06 complete
- [ ] AI-07 complete
- [ ] AI-08 complete

