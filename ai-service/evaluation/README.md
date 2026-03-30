# AI Evaluation Baseline (Sprint AI-03)

This folder contains a standalone benchmark workflow for evaluating text moderation quality using the existing orchestration pipeline in text-only mode.

The benchmark is intentionally isolated from production code and API routes.

## Structure

- `datasets/benchmark_v1.json`: curated benchmark samples
- `datasets/hard_cases_v1.json`: stress cases (Arabizi, mixed language, OCR-noise tokens, punctuation, borderline educational)
- `scripts/compute_metrics.py`: metric helpers (accuracy, range checks, PR/F1, confusion matrix)
- `scripts/run_benchmark.py`: benchmark runner and markdown report generator
- `reports/baseline_v1.md`: generated report artifact

## How it works

The runner calls:

`build_analyze_response_from_plain_text(text, image=None)`

This keeps the same text pipeline behavior (including OCR cleanup + dialect + educational scoring) while skipping vision inference.

## Run

From `ai-service/`:

```bash
python evaluation/scripts/run_benchmark.py
```

It generates:

`evaluation/reports/baseline_v1.md`

### Hard cases (`--hard`)

The hard-cases dataset targets challenging inputs: Arabizi variants (including mixed case), mixed Arabic/English lines, OCR-style noise tokens, punctuation-heavy forms, borderline educational phrasing, and representative Arabic safe/risky/dangerous/educational lines. Dialect-triggered rows include `tunisian_dialect_risk` in `expectedLabels` where applicable; educational rows use the keyword label `educational content` to match the text pipeline.

From `ai-service/`:

```bash
python evaluation/scripts/run_benchmark.py --hard
```

This loads `evaluation/datasets/hard_cases_v1.json` and writes `evaluation/reports/baseline_hard_v1.md` by default. Use the report as a robustness baseline: lower scores here indicate where multilingual and noisy-input behavior should improve over time.

You can override the report filename in either mode:

```bash
python evaluation/scripts/run_benchmark.py --hard --report-name my_hard_run.md
```

Optional (default benchmark):

```bash
python evaluation/scripts/run_benchmark.py --report-name baseline_v2.md --changes-note "- tuned thresholds ..."
```

## Dataset schema

Required:

- `id`: unique case id
- `text`: input text
- `expectedCategory`: one of `safe`, `risky`, `dangerous`, `educational`

Optional:

- `expectedLabels`: expected matched keywords list
- `expectedRiskMin`, `expectedRiskMax`: expected risk range
- `expectedEducational`: boolean expected educational flag
- `expectedEducationalMin`, `expectedEducationalMax`: expected educational score range
- `language`, `slice`, `expectFallback`: metadata for subset analysis

## Metrics produced

- category accuracy
- risk-range pass rate
- educational-range pass rate
- educational-boolean accuracy
- per-label precision/recall/F1
- category confusion matrix
- focused subset metrics:
  - dialect recall (`tunisian_dialect_risk`)
  - educational positive recall

## Extending benchmark

- Add new samples in `datasets/benchmark_v1.json`
- Keep field names stable for script compatibility
- For next iteration, copy to `benchmark_v2.json` and expand slices/failure-driven cases

