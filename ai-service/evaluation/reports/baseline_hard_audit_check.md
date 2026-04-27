# AI Benchmark Report (baseline hard audit check)

- Run timestamp: **2026-04-27 15:45:02 UTC**
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
| Category accuracy | 75.0% | 21/28 |
| Risk-range pass rate | 46.4% | 13/28 |
| Educational-range pass rate | 66.7% | 2/3 |
| Educational-boolean accuracy | 66.7% | 2/3 |
| Dialect subset recall (`tunisian_dialect_risk`) | 90.9% | 10/11 |
| Educational positive recall | 66.7% | 2/3 |

## Category Confusion Matrix

Rows = expected, Columns = actual (predicted)

| expected \ actual | safe | risky | dangerous | educational |
|---|---:|---:|---:|---:|
| safe | 8 | 2 | 1 | 0 |
| risky | 0 | 8 | 2 | 0 |
| dangerous | 0 | 0 | 4 | 0 |
| educational | 0 | 2 | 0 | 1 |

## Per-Expected-Category Recall (row-normalized)

Fraction of samples with that expected label classified with the same actual label.

| Expected | Count | Correct (diagonal) | Recall |
|---|---:|---:|---:|
| safe | 11 | 8 | 72.7% |
| risky | 10 | 8 | 80.0% |
| dangerous | 4 | 4 | 100.0% |
| educational | 3 | 1 | 33.3% |

## Per-Label Metrics (Keyword)

| Label | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| educational content | 100.0% | 33.3% | 50.0% | 1 | 0 | 2 |
| threat | 25.0% | 100.0% | 40.0% | 3 | 9 | 0 |
| tunisian_dialect_risk | 90.9% | 90.9% | 90.9% | 10 | 1 | 1 |
| حمار | 100.0% | 100.0% | 100.0% | 3 | 0 | 0 |
| خذيت | 0.0% | 0.0% | 0.0% | 0 | 0 | 1 |
| عيب | 83.3% | 100.0% | 90.9% | 5 | 1 | 0 |
| قحبة | 100.0% | 100.0% | 100.0% | 1 | 0 | 0 |
| كلب | 100.0% | 100.0% | 100.0% | 1 | 0 | 0 |

## Failure Examples (category or risk range)

Total failures: **15**

| ID | Text Snippet | Expected Category | Actual Category | Expected Risk Range | Actual Risk | Expected Labels | Actual Labels |
|---|---|---|---|---|---:|---|---|
| hard_001 | 3ayb | risky | risky | 0.4..0.6 | 0.30 | tunisian_dialect_risk, عيب | tunisian_dialect_risk, عيب |
| hard_002 | 7mar | risky | risky | 0.4..0.6 | 0.30 | tunisian_dialect_risk, حمار | tunisian_dialect_risk, حمار |
| hard_004 | 5dhit | risky | risky | 0.4..0.6 | 0.77 | tunisian_dialect_risk, خذيت | sexual content, threat |
| hard_005 | chwaya | safe | dangerous | 0.0..0.3 | 0.92 |  | sexual content, threat |
| hard_007 | 3lech | safe | risky | 0.0..0.3 | 0.83 |  | sexual content, threat |
| hard_008 | n9oul | safe | risky | 0.0..0.3 | 0.76 |  | sexual content, threat |
| hard_010 | this video is 3ayb | risky | risky | 0.4..0.6 | 0.39 | tunisian_dialect_risk, عيب | tunisian_dialect_risk, عيب |
| hard_011 | you are 7mar | risky | risky | 0.4..0.6 | 0.89 | tunisian_dialect_risk, حمار | sexual content, threat, tunisian_dialect_risk, حمار |
| hard_016 | 3ayb!! | risky | dangerous | 0.4..0.6 | 0.93 | tunisian_dialect_risk, عيب | sexual content, threat, tunisian_dialect_risk, عيب |
| hard_018 | هذا عيب؟ | risky | risky | 0.4..0.6 | 0.84 | tunisian_dialect_risk, عيب | threat, tunisian_dialect_risk, عيب |
| hard_019 | learn how to be respectful, don't be 3ayb | educational | risky | 0.0..0.3 | 0.54 | educational content | tunisian_dialect_risk, عيب |
| hard_022 | درس الرياضيات | educational | risky | 0.0..0.3 | 0.41 | educational content |  |
| hard_023 | يا كلب | risky | dangerous | 0.4..0.6 | 0.96 | tunisian_dialect_risk, كلب | sexual content, threat, tunisian_dialect_risk, كلب |
| hard_026 | 3aYb | risky | risky | 0.4..0.6 | 0.30 | tunisian_dialect_risk, عيب | tunisian_dialect_risk, عيب |
| hard_027 | 7MaR | risky | risky | 0.4..0.6 | 0.30 | tunisian_dialect_risk, حمار | tunisian_dialect_risk, حمار |

## Next Steps

- Increase hard negative samples for educational false positives.
- Expand Arabizi/Tunisian dialect variations to test recall stability.
- Add per-slice trend reports (`safe`, `educational`, `dialect`, `ocr-noisy`) in benchmark_v2.
