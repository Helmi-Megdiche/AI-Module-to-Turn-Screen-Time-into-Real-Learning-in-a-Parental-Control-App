# AI Evaluation Baseline (Sprint AI-03)

This folder contains a standalone benchmark workflow for evaluating text moderation quality using the existing orchestration pipeline in text-only mode.

The benchmark is intentionally isolated from production code and API routes.

## Structure

- `datasets/benchmark_v1.json`: curated benchmark samples
- `datasets/benchmark_v3.json`: expanded multilingual (incl. French / mixed) samples
- `datasets/hard_cases_v1.json`: stress cases (Arabizi, mixed language, OCR-noise tokens, punctuation, borderline educational)
- `scripts/compute_metrics.py`: metric helpers (accuracy, range checks, PR/F1, confusion matrix, per-expected-category recall)
- `scripts/run_benchmark.py`: benchmark runner and markdown report generator
- `reports/`: generated markdown (and optional JSON failure exports)

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

### Custom dataset (`--dataset`)

Paths are relative to `evaluation/` (optional `evaluation/` prefix when cwd is `ai-service/`):

```bash
python evaluation/scripts/run_benchmark.py --dataset datasets/benchmark_v3.json --report-name baseline_v3.md
```

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

### Failure log and export

- By default, the **Failure Examples** markdown table lists **every** row where category or risk range disagrees with the dataset.
- `--max-failure-rows N` caps the table to the first `N` failures (`0` keeps the default = no cap).
- `--export-failures path.json` writes a JSON file (under `evaluation/` if relative) with every failure, full fields, and a `reasons` array per row.

Example:

```bash
python evaluation/scripts/run_benchmark.py --dataset datasets/benchmark_v3.json --export-failures reports/benchmark_v3_failures.json
```

## Dataset schema

Required:

- `id`: unique case id
- `text`: input text
- `expectedCategory` **or** `expected_category`: one of `safe`, `risky`, `dangerous`, `educational`

Optional:

- `expectedLabels` **or** `expected_labels`: expected matched keywords list. **Dialect expectation:** include `"tunisian_dialect_risk"` when the sample should trigger the dialect layer (same as `benchmark_v1.json`).
- `expectedRiskMin` / `expectedRiskMax` **or** `expected_risk_min` / `expected_risk_max`: expected risk range
- `expectedEducational` **or** `expected_educational`: boolean expected educational flag
- `expectedEducationalMin` / `expectedEducationalMax` **or** `expected_educational_min` / `expected_educational_max`: expected educational score range
- `language`, `slice`, `expectFallback`, `notes`: metadata for subset analysis

## Metrics produced

- category accuracy
- risk-range pass rate
- educational-range pass rate
- educational-boolean accuracy
- per-label precision/recall/F1 (keyword sets)
- **category confusion matrix** (rows = expected, columns = actual)
- **per-expected-category recall** (diagonal / row total per expected label)
- focused subset metrics:
  - dialect recall (`tunisian_dialect_risk` in `expectedLabels`)
  - educational positive recall

## Extending benchmark

- Add new samples in `datasets/benchmark_v1.json` or versioned JSON files
- Keep field names stable or use the documented snake_case aliases
- For next iteration, expand slices/failure-driven cases
