# AI Benchmark Report (baseline hard v1)

- Run timestamp: **2026-03-30 16:16:57 UTC**
- Dataset: `C:/Users/helmi/OneDrive/Bureau/PFE/AI-Module-to-Turn-Screen-Time-into-Real-Learning-in-a-Parental-Control-App/ai-service/evaluation/datasets/hard_cases_v1.json`
- Total samples: **28**
- Mode: `build_analyze_response_from_plain_text(text, image=None)`
- Thresholds:
  - `RISKY_THRESHOLD=0.4`
  - `DANGEROUS_THRESHOLD=0.95`
  - `EDUCATIONAL_THRESHOLD=0.55`

## Summary Metrics

| Metric | Value | Numerator/Denominator |
|---|---:|---:|
| Category accuracy | 42.9% | 12/28 |
| Risk-range pass rate | 42.9% | 12/28 |
| Educational-range pass rate | 66.7% | 2/3 |
| Educational-boolean accuracy | 66.7% | 2/3 |
| Dialect subset recall (`tunisian_dialect_risk`) | 90.9% | 10/11 |
| Educational positive recall | 66.7% | 2/3 |

## Category Confusion Matrix

Rows = expected, Columns = actual

| expected \ actual | safe | risky | dangerous | educational |
|---|---:|---:|---:|---:|
| safe | 5 | 4 | 0 | 2 |
| risky | 5 | 4 | 1 | 0 |
| dangerous | 0 | 2 | 2 | 0 |
| educational | 1 | 1 | 0 | 1 |

## Per-Label Metrics (Keyword)

| Label | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| educational content | 16.7% | 100.0% | 28.6% | 3 | 15 | 0 |
| threat | 23.1% | 100.0% | 37.5% | 3 | 10 | 0 |
| tunisian_dialect_risk | 90.9% | 90.9% | 90.9% | 10 | 1 | 1 |
| حمار | 100.0% | 100.0% | 100.0% | 3 | 0 | 0 |
| خذيت | 0.0% | 0.0% | 0.0% | 0 | 0 | 1 |
| عيب | 83.3% | 100.0% | 90.9% | 5 | 1 | 0 |
| قحبة | 100.0% | 100.0% | 100.0% | 1 | 0 | 0 |
| كلب | 100.0% | 100.0% | 100.0% | 1 | 0 | 0 |

## Failure Examples

| ID | Text Snippet | Expected Category | Actual Category | Expected Risk Range | Actual Risk | Expected Labels | Actual Labels |
|---|---|---|---|---|---:|---|---|
| hard_001 | 3ayb | risky | safe | 0.4..0.6 | 0.10 | tunisian_dialect_risk, عيب | tunisian_dialect_risk, عيب |
| hard_002 | 7mar | risky | safe | 0.4..0.6 | 0.10 | tunisian_dialect_risk, حمار | tunisian_dialect_risk, حمار |
| hard_003 | 9ahba | dangerous | risky | 0.85..1.0 | 0.91 | tunisian_dialect_risk, قحبة | sexual content, threat, tunisian_dialect_risk, قحبة, educational content |
| hard_004 | 5dhit | risky | risky | 0.4..0.6 | 0.77 | tunisian_dialect_risk, خذيت | sexual content, threat, educational content |
| hard_005 | chwaya | safe | risky | 0.0..0.3 | 0.92 |  | sexual content, threat, educational content |
| hard_007 | 3lech | safe | risky | 0.0..0.3 | 0.83 |  | sexual content, threat, educational content |
| hard_008 | n9oul | safe | risky | 0.0..0.3 | 0.76 |  | sexual content, threat, educational content |
| hard_010 | this video is 3ayb | risky | safe | 0.4..0.6 | 0.19 | tunisian_dialect_risk, عيب | tunisian_dialect_risk, عيب |
| hard_011 | you are 7mar | risky | risky | 0.4..0.6 | 0.89 | tunisian_dialect_risk, حمار | sexual content, threat, tunisian_dialect_risk, حمار, educational content |
| hard_015 | 5dhit5 | safe | risky | 0.0..0.3 | 0.75 |  | sexual content, threat, educational content |

## Next Steps

- Increase hard negative samples for educational false positives.
- Expand Arabizi/Tunisian dialect variations to test recall stability.
- Add per-slice trend reports (`safe`, `educational`, `dialect`, `ocr-noisy`) in benchmark_v2.
