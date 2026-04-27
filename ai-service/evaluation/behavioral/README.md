# Behavioral Benchmark (Phase 6a)

This folder contains the deterministic benchmark framework for AI-07 behavioral
scoring and recommendation quality.

## Structure

- `datasets/behavioral_profiles_v1.json`: 15 synthetic profile definitions
- `scripts/synthetic_profile.py`: deterministic event generator (`random.Random(seed)`)
- `scripts/run_behavioral_benchmark.py`: benchmark runner + markdown report writer
- `reports/`: generated reports and optional JSON exports

## Determinism

All synthetic events are generated from:

- a fixed reference end date (`2026-04-20`)
- profile generator parameters
- a local `random.Random(seed)` instance

No `numpy` or ML randomness is used.

## Run

From `ai-service/`:

```bash
python -m evaluation.behavioral.scripts.run_behavioral_benchmark \
  --profiles evaluation/behavioral/datasets/behavioral_profiles_v1.json \
  --report-name first_run_actuals.md \
  --export-actuals evaluation/behavioral/reports/first_run_actuals.json
```

The runner always executes all profiles and exits with code `0`, even when
required/forbidden recommendation checks fail; those diagnostics are reported in
the markdown output.
