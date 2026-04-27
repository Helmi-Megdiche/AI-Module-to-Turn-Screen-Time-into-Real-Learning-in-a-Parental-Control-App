# Behavioral Benchmark Report (actuals)

## Run metadata

- Timestamp UTC: **2026-04-27 16:19:19 UTC**
- Scorer version: **Phase 6b**
- Profiles file: `C:/Users/helmi/AppData/Local/Temp/pytest-of-helmi/pytest-26/test_runner_main_returns_zero_0/failing_profiles.json`
- Total profile count: **1**
- Score range pass rate: **N/A (run without --assert-ranges)**
- Required-recommendation pass rate: **0/1**
- Forbidden-recommendation pass rate: **1/1**
- Missions expected-subset pass rate: **1/1**

## Headline metrics

- Score range pass rate: **N/A**
- Required-recommendation pass rate: **0/1 (0.0%)**
- Forbidden-recommendation pass rate: **1/1 (100.0%)**
- Missions expected-subset pass rate: **1/1 (100.0%)**
- Combined pass rate (all green): **0/1 (0.0%)**

## Category distribution

| Distribution | low | moderate | high |
|---|---:|---:|---:|
| Addiction | 1 | 0 | 0 |
| Wellbeing | 0 | 1 | 0 |

| Age bracket | Count |
|---|---:|
| 2-5 | 0 |
| 6-12 | 1 |
| 13-18 | 0 |
| other | 0 |

## Recommendation rule coverage

| Rule | Severity | Triggered by profile ids | Coverage |
|---|---|---|---|
| screen_curfew | high | - | ✗ |
| weekly_escalation_alert | high | - | ✗ |
| daily_limit_reminder | medium | - | ✗ |
| session_break | medium | - | ✗ |
| imbalance_warning | medium | failing_case | ✓ |
| real_activity_prompt | medium | failing_case | ✓ |
| educational_boost | low | - | ✗ |
| family_time_suggestion | low | failing_case | ✓ |
| balance_celebration | positive | - | ✗ |
- Rule coverage rate: **3/9**

## Profile summary table

| id | age | addiction (range) | wellbeing (range) | triggered | Missions | range_ok | required_ok | forbidden_ok | missions_ok |
|---|---:|---|---|---|---|---|---|---|---|
| failing_case | 9 | 0.150 (-) | 0.400 (-) | imbalance_warning, real_activity_prompt, family_time_suggestion | real_activity, family_interaction | N/A | False | True | True |

## Per-profile details

### failing_case

- Description: profile intentionally forcing expectation mismatch
- Age: 9
- Seed: 1
- Generated events: 0
- addiction_score: 0.150
- wellbeing_score: 0.400
- expected_addiction_range: None
- expected_wellbeing_range: None
- Triggered recommendations: imbalance_warning, real_activity_prompt, family_time_suggestion
- Required recommendations: screen_curfew
- Forbidden recommendations: -
- Triggered missions: real_activity, family_interaction
- Expected missions: -
- range_ok: N/A
- required_ok: False
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=None | wellbeing=None

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.000 |
| addiction | compulsivity | 0.000 |
| addiction | nocturnal | 0.000 |
| addiction | escalation | 0.000 |
| addiction | imbalance | 1.000 |
| wellbeing | screen_balance | 1.000 |
| wellbeing | content_quality | 0.000 |
| wellbeing | real_activity | 0.000 |
| wellbeing | sleep | 1.000 |
| wellbeing | family_interaction | 0.000 |

## Reproducibility

- Determinism: generator uses only local `random.Random(seed)`.
- No numpy or external stochastic library used.
- Reproduce command: `\.venv\Scripts\python.exe -m evaluation.behavioral.scripts.run_behavioral_benchmark --profiles C:/Users/helmi/AppData/Local/Temp/pytest-of-helmi/pytest-26/test_runner_main_returns_zero_0/failing_profiles.json --report-name phase6a_test.md`
- Seed list per profile:
| id | seed |
|---|---:|
| failing_case | 1 |

## Methodology

- Profiles are synthetic clinical archetypes (15 fixed seeds, 14-day windows).
- Scores use saturating calibration (`saturating_score`, `steepness=0.5`).
- Expected ranges are calibrated from empirical second-run actuals with tolerance ±0.08.
- Recommendation thresholds are calibrated in Phase 6b for clinical sensitivity and specificity.

## Limitations

- Profiles are synthetic; no real field telemetry is used yet.
- Scoring and recommendations are rule-based; no supervised ML layer is used.
- Circadian patterns are simplified (weekend behavior uses multiplier).

## Clinical source citations

- American Academy of Pediatrics (AAP), *Media and Young Minds* (2016)
- World Health Organization (WHO), sedentary behavior guidelines (2019)
- American Academy of Sleep Medicine (AASM), pediatric sleep recommendations (2014)
- Panova & Carbonell, smartphone addiction critique (2018)
- Kwon et al., Smartphone Addiction Scale (2013)
