# AI Benchmark Report (baseline hard v2)

- Run timestamp: **2026-03-30 16:51:46 UTC**
- Dataset: `C:/Users/helmi/OneDrive/Bureau/PFE/AI-Module-to-Turn-Screen-Time-into-Real-Learning-in-a-Parental-Control-App/ai-service/evaluation/datasets/hard_cases_v1.json`
- Total samples: **28**
- Mode: `build_analyze_response_from_plain_text(text, image=None)`
- Thresholds:
  - `RISKY_THRESHOLD=0.3`
  - `DANGEROUS_THRESHOLD=0.9`
  - `EDUCATIONAL_THRESHOLD=0.55`

## Summary Metrics

| Metric | Value | Numerator/Denominator |
|---|---:|---:|
| Category accuracy | 42.9% | 12/28 |
| Risk-range pass rate | 46.4% | 13/28 |
| Educational-range pass rate | 66.7% | 2/3 |
| Educational-boolean accuracy | 66.7% | 2/3 |
| Dialect subset recall (`tunisian_dialect_risk`) | 90.9% | 10/11 |
| Educational positive recall | 66.7% | 2/3 |

## Category Confusion Matrix

Rows = expected, Columns = actual

| expected \ actual | safe | risky | dangerous | educational |
|---|---:|---:|---:|---:|
| safe | 6 | 2 | 1 | 2 |
| risky | 5 | 1 | 4 | 0 |
| dangerous | 0 | 0 | 4 | 0 |
| educational | 0 | 2 | 0 | 1 |

## Per-Label Metrics (Keyword)

| Label | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| educational content | 33.3% | 33.3% | 33.3% | 1 | 2 | 2 |
| threat | 25.0% | 100.0% | 40.0% | 3 | 9 | 0 |
| tunisian_dialect_risk | 90.9% | 90.9% | 90.9% | 10 | 1 | 1 |
| حمار | 100.0% | 100.0% | 100.0% | 3 | 0 | 0 |
| خذيت | 0.0% | 0.0% | 0.0% | 0 | 0 | 1 |
| عيب | 83.3% | 100.0% | 90.9% | 5 | 1 | 0 |
| قحبة | 100.0% | 100.0% | 100.0% | 1 | 0 | 0 |
| كلب | 100.0% | 100.0% | 100.0% | 1 | 0 | 0 |

## Failure Examples

| ID | Text Snippet | Expected Category | Actual Category | Expected Risk Range | Actual Risk | Expected Labels | Actual Labels |
|---|---|---|---|---|---:|---|---|
| hard_001 | 3ayb | risky | safe | 0.4..0.6 | 0.20 | tunisian_dialect_risk, عيب | tunisian_dialect_risk, عيب |
| hard_002 | 7mar | risky | safe | 0.4..0.6 | 0.20 | tunisian_dialect_risk, حمار | tunisian_dialect_risk, حمار |
| hard_004 | 5dhit | risky | risky | 0.4..0.6 | 0.77 | tunisian_dialect_risk, خذيت | sexual content, threat |
| hard_005 | chwaya | safe | dangerous | 0.0..0.3 | 0.92 |  | sexual content, threat |
| hard_007 | 3lech | safe | risky | 0.0..0.3 | 0.83 |  | sexual content, threat |
| hard_008 | n9oul | safe | risky | 0.0..0.3 | 0.76 |  | sexual content, threat |
| hard_010 | this video is 3ayb | risky | safe | 0.4..0.6 | 0.29 | tunisian_dialect_risk, عيب | tunisian_dialect_risk, عيب |
| hard_011 | you are 7mar | risky | dangerous | 0.4..0.6 | 0.99 | tunisian_dialect_risk, حمار | sexual content, threat, tunisian_dialect_risk, حمار |
| hard_016 | 3ayb!! | risky | dangerous | 0.4..0.6 | 1.00 | tunisian_dialect_risk, عيب | sexual content, threat, tunisian_dialect_risk, عيب |
| hard_018 | هذا عيب؟ | risky | dangerous | 0.4..0.6 | 0.94 | tunisian_dialect_risk, عيب | threat, sexual content, tunisian_dialect_risk, عيب |

## Next Steps

- Increase hard negative samples for educational false positives.
- Expand Arabizi/Tunisian dialect variations to test recall stability.
- Add per-slice trend reports (`safe`, `educational`, `dialect`, `ocr-noisy`) in benchmark_v2.
