# AI Benchmark Report (baseline v2)

- Run timestamp: **2026-03-30 13:21:52 UTC**
- Dataset: `C:/Users/helmi/OneDrive/Bureau/PFE/AI-Module-to-Turn-Screen-Time-into-Real-Learning-in-a-Parental-Control-App/ai-service/evaluation/datasets/benchmark_v1.json`
- Total samples: **24**
- Mode: `build_analyze_response_from_plain_text(text, image=None)`
- Thresholds:
  - `RISKY_THRESHOLD=0.4`
  - `DANGEROUS_THRESHOLD=0.95`
  - `EDUCATIONAL_THRESHOLD=0.55`

## Summary Metrics

| Metric | Value | Numerator/Denominator |
|---|---:|---:|
| Category accuracy | 75.0% | 18/24 |
| Risk-range pass rate | 79.2% | 19/24 |
| Educational-range pass rate | 83.3% | 5/6 |
| Educational-boolean accuracy | 91.7% | 22/24 |
| Dialect subset recall (`tunisian_dialect_risk`) | 100.0% | 3/3 |
| Educational positive recall | 100.0% | 5/5 |

## Category Confusion Matrix

Rows = expected, Columns = actual

| expected \ actual | safe | risky | dangerous | educational |
|---|---:|---:|---:|---:|
| safe | 4 | 0 | 0 | 0 |
| risky | 1 | 4 | 4 | 0 |
| dangerous | 0 | 1 | 5 | 0 |
| educational | 0 | 0 | 0 | 5 |

## Per-Label Metrics (Keyword)

| Label | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| educational content | 23.8% | 100.0% | 38.5% | 5 | 16 | 0 |
| harassment | 33.3% | 66.7% | 44.4% | 2 | 4 | 1 |
| hate speech | 37.5% | 100.0% | 54.5% | 3 | 5 | 0 |
| self-harm | 20.0% | 50.0% | 28.6% | 1 | 4 | 1 |
| sexual content | 0.0% | 0.0% | 0.0% | 0 | 13 | 1 |
| threat | 30.8% | 100.0% | 47.1% | 4 | 9 | 0 |
| tunisian_dialect_risk | 100.0% | 100.0% | 100.0% | 3 | 0 | 0 |
| violence | 30.0% | 100.0% | 46.2% | 3 | 7 | 0 |

## Failure Examples

| ID | Text Snippet | Expected Category | Actual Category | Expected Risk Range | Actual Risk | Expected Labels | Actual Labels |
|---|---|---|---|---|---:|---|---|
| b003-ricky-en-harassment | You are disgusting and everyone in class hates you. | risky | dangerous | 0.4..0.85 | 0.98 | harassment, hate speech | sexual content, hate speech, threat, violence, harassment, educational content |
| b006-risky-en-sexual | This video contains explicit sexual scenes and nudity. | risky | safe | 0.4..0.95 | 0.02 | sexual content |  |
| b009-risky-ar-harassment | أنت غبي ولا أحد يحبك | risky | dangerous | 0.4..0.85 | 0.97 | harassment | sexual content, harassment, threat, hate speech, violence, educational content |
| b012-risky-arabizi-3ayb | 3ayb kifeh tahki haka | risky | dangerous | 0.1..1.0 | 1.00 | tunisian_dialect_risk | sexual content, threat, tunisian_dialect_risk, عيب, educational content |
| b015-mixed-fr-en-hate | Tous les immigrés sont des rats. I hate them all. | dangerous | risky | 0.75..1.0 | 0.92 | hate speech | hate speech, sexual content, threat, violence, harassment, self-harm, educational content |
| b021-risky-fr-bullying | Tu es nul, personne ne veut de toi en classe. | risky | risky | 0.4..0.85 | 0.93 | harassment | sexual content, educational content |
| b024-risky-en-hate | People from that religion are disgusting and should be excluded. | risky | dangerous | 0.4..0.95 | 0.97 | hate speech | threat, hate speech, sexual content, harassment, violence, self-harm, educational content |

## Next Steps

- Increase hard negative samples for educational false positives.
- Expand Arabizi/Tunisian dialect variations to test recall stability.
- Add per-slice trend reports (`safe`, `educational`, `dialect`, `ocr-noisy`) in benchmark_v2.

## Changes from v1

- Raised MODERATION_DANGEROUS_THRESHOLD default from 0.85 to 0.95.
- Raised Tunisian fuzzy latin cutoff from 0.80 to 0.85.
- Added non-breaking post-rules in analysis_orchestrator: (1) downgrade educational-only risky outputs to safe with capped risk, (2) suppress educational_score boolean in harmful contexts while preserving keyword explainability.

Comparison vs original baseline_v1 (before AI-04 tuning):
- Category accuracy: 58.3% -> 75.0% (+16.7 pts)
- Risk-range pass rate: 75.0% -> 79.2% (+4.2 pts)
- Educational boolean accuracy: 33.3% -> 91.7% (+58.4 pts)
