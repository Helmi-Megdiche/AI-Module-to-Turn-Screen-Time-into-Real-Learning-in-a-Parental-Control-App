# Behavioral Benchmark Report (actuals)

## Run metadata

- Timestamp UTC: **2026-04-27 15:22:15 UTC**
- Scorer version: **Phase 6b**
- Profiles file: `C:/Users/helmi/OneDrive/Bureau/PFE/AI-Module-to-Turn-Screen-Time-into-Real-Learning-in-a-Parental-Control-App/ai-service/evaluation/behavioral/datasets/behavioral_profiles_v1.json`
- Total profile count: **15**
- Score range pass rate: **15/15**
- Required-recommendation pass rate: **15/15**
- Forbidden-recommendation pass rate: **15/15**
- Missions expected-subset pass rate: **15/15**

## Headline metrics

- Score range pass rate: **15/15 (100.0%)**
- Required-recommendation pass rate: **15/15 (100.0%)**
- Forbidden-recommendation pass rate: **15/15 (100.0%)**
- Missions expected-subset pass rate: **15/15 (100.0%)**
- Combined pass rate (all green): **15/15 (100.0%)**

## Category distribution

| Distribution | low | moderate | high |
|---|---:|---:|---:|
| Addiction | 9 | 2 | 4 |
| Wellbeing | 3 | 7 | 5 |

| Age bracket | Count |
|---|---:|
| 2-5 | 0 |
| 6-12 | 11 |
| 13-18 | 4 |
| other | 0 |

## Recommendation rule coverage

| Rule | Severity | Triggered by profile ids | Coverage |
|---|---|---|---|
| screen_curfew | high | nocturnal_teen_15yo, sleep_deprived_10yo | ✓ |
| weekly_escalation_alert | high | heavy_escalating_12yo, rising_concern_9yo | ✓ |
| daily_limit_reminder | medium | social_media_heavy_14yo, sleep_deprived_10yo | ✓ |
| session_break | medium | compulsive_user_10yo, social_media_heavy_14yo | ✓ |
| imbalance_warning | medium | heavy_escalating_12yo, nocturnal_teen_15yo, social_media_heavy_14yo, sleep_deprived_10yo, low_engagement_8yo, edge_case_zero_usage | ✓ |
| real_activity_prompt | medium | social_media_heavy_14yo, low_engagement_8yo, edge_case_zero_usage | ✓ |
| educational_boost | low | heavy_escalating_12yo, nocturnal_teen_15yo, compulsive_user_10yo, social_media_heavy_14yo, sleep_deprived_10yo | ✓ |
| family_time_suggestion | low | edge_case_zero_usage | ✓ |
| balance_celebration | positive | balanced_child_8yo, educational_focused_9yo, moderate_family_7yo, balanced_teen_16yo, pure_educational_7yo | ✓ |
- Rule coverage rate: **9/9**

## Profile summary table

| id | age | addiction (range) | wellbeing (range) | triggered | Missions | range_ok | required_ok | forbidden_ok | missions_ok |
|---|---:|---|---|---|---|---|---|---|---|
| balanced_child_8yo | 8 | 0.093 (0.013-0.173) | 0.842 (0.762-0.922) | balance_celebration | - | True | True | True | True |
| heavy_escalating_12yo | 12 | 0.404 (0.324-0.484) | 0.477 (0.397-0.557) | weekly_escalation_alert, imbalance_warning, educational_boost | content_quality, real_activity | True | True | True | True |
| nocturnal_teen_15yo | 15 | 0.425 (0.345-0.505) | 0.326 (0.246-0.406) | screen_curfew, imbalance_warning, educational_boost | content_quality, nocturnal | True | True | True | True |
| compulsive_user_10yo | 10 | 0.344 (0.264-0.424) | 0.563 (0.483-0.643) | session_break, educational_boost | content_quality, compulsivity | True | True | True | True |
| educational_focused_9yo | 9 | 0.152 (0.072-0.232) | 0.791 (0.711-0.871) | balance_celebration | - | True | True | True | True |
| moderate_family_7yo | 7 | 0.103 (0.023-0.183) | 0.841 (0.761-0.921) | balance_celebration | - | True | True | True | True |
| weekend_spike_11yo | 11 | 0.161 (0.081-0.241) | 0.670 (0.590-0.750) | - | content_quality | True | True | True | True |
| social_media_heavy_14yo | 14 | 0.451 (0.371-0.531) | 0.336 (0.256-0.416) | daily_limit_reminder, session_break, imbalance_warning, real_activity_prompt, educational_boost | content_quality, real_activity | True | True | True | True |
| post_intervention_recovering_13yo | 13 | 0.187 (0.107-0.267) | 0.661 (0.581-0.741) | - | content_quality | True | True | True | True |
| sleep_deprived_10yo | 10 | 0.468 (0.388-0.548) | 0.295 (0.215-0.375) | screen_curfew, daily_limit_reminder, imbalance_warning, educational_boost | nocturnal, sleep | True | True | True | True |
| low_engagement_8yo | 8 | 0.178 (0.098-0.258) | 0.443 (0.363-0.523) | imbalance_warning, real_activity_prompt | real_activity, family_interaction | True | True | True | True |
| balanced_teen_16yo | 16 | 0.143 (0.063-0.223) | 0.747 (0.667-0.827) | balance_celebration | - | True | True | True | True |
| rising_concern_9yo | 9 | 0.340 (0.260-0.420) | 0.596 (0.516-0.676) | weekly_escalation_alert | content_quality, escalation | True | True | True | True |
| pure_educational_7yo | 7 | 0.056 (0.000-0.136) | 0.925 (0.845-1.000) | balance_celebration | - | True | True | True | True |
| edge_case_zero_usage | 10 | 0.150 (0.070-0.230) | 0.400 (0.320-0.480) | imbalance_warning, real_activity_prompt, family_time_suggestion | real_activity, family_interaction | True | True | True | True |

## Per-profile details

### balanced_child_8yo

- Description: Enfant équilibré, 1h d'écran par jour, missions assidues, contenu éducatif
- Age: 8
- Seed: 101
- Generated events: 140
- addiction_score: 0.093
- wellbeing_score: 0.842
- expected_addiction_range: [0.013, 0.173]
- expected_wellbeing_range: [0.762, 0.922]
- Triggered recommendations: balance_celebration
- Required recommendations: balance_celebration
- Forbidden recommendations: daily_limit_reminder, screen_curfew, session_break, weekly_escalation_alert
- Triggered missions: -
- Expected missions: -
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.013, 0.173] | wellbeing=[0.762, 0.922]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.237 |
| addiction | compulsivity | 0.020 |
| addiction | nocturnal | 0.000 |
| addiction | escalation | 0.000 |
| addiction | imbalance | 0.200 |
| wellbeing | screen_balance | 0.763 |
| wellbeing | content_quality | 0.800 |
| wellbeing | real_activity | 0.800 |
| wellbeing | sleep | 1.000 |
| wellbeing | family_interaction | 0.860 |

### heavy_escalating_12yo

- Description: Usage intensif avec hausse hebdomadaire marquée
- Age: 12
- Seed: 102
- Generated events: 644
- addiction_score: 0.404
- wellbeing_score: 0.477
- expected_addiction_range: [0.324, 0.484]
- expected_wellbeing_range: [0.397, 0.557]
- Triggered recommendations: weekly_escalation_alert, imbalance_warning, educational_boost
- Required recommendations: weekly_escalation_alert
- Forbidden recommendations: balance_celebration
- Triggered missions: content_quality, real_activity
- Expected missions: content_quality, real_activity
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.324, 0.484] | wellbeing=[0.397, 0.557]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.455 |
| addiction | compulsivity | 0.119 |
| addiction | nocturnal | 0.154 |
| addiction | escalation | 0.637 |
| addiction | imbalance | 0.725 |
| wellbeing | screen_balance | 0.545 |
| wellbeing | content_quality | 0.250 |
| wellbeing | real_activity | 0.300 |
| wellbeing | sleep | 0.846 |
| wellbeing | family_interaction | 0.510 |

### nocturnal_teen_15yo

- Description: Adolescent avec usage nocturne prolongé
- Age: 15
- Seed: 103
- Generated events: 490
- addiction_score: 0.425
- wellbeing_score: 0.326
- expected_addiction_range: [0.345, 0.505]
- expected_wellbeing_range: [0.246, 0.406]
- Triggered recommendations: screen_curfew, imbalance_warning, educational_boost
- Required recommendations: screen_curfew
- Forbidden recommendations: balance_celebration
- Triggered missions: content_quality, nocturnal
- Expected missions: nocturnal
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.345, 0.505] | wellbeing=[0.246, 0.406]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.496 |
| addiction | compulsivity | 0.059 |
| addiction | nocturnal | 0.834 |
| addiction | escalation | 0.048 |
| addiction | imbalance | 0.750 |
| wellbeing | screen_balance | 0.504 |
| wellbeing | content_quality | 0.100 |
| wellbeing | real_activity | 0.400 |
| wellbeing | sleep | 0.166 |
| wellbeing | family_interaction | 0.580 |

### compulsive_user_10yo

- Description: Usage compulsif: sessions courtes très fréquentes
- Age: 10
- Seed: 104
- Generated events: 4494
- addiction_score: 0.344
- wellbeing_score: 0.563
- expected_addiction_range: [0.264, 0.424]
- expected_wellbeing_range: [0.483, 0.643]
- Triggered recommendations: session_break, educational_boost
- Required recommendations: session_break
- Forbidden recommendations: balance_celebration
- Triggered missions: content_quality, compulsivity
- Expected missions: compulsivity
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.264, 0.424] | wellbeing=[0.483, 0.643]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.406 |
| addiction | compulsivity | 0.664 |
| addiction | nocturnal | 0.080 |
| addiction | escalation | 0.000 |
| addiction | imbalance | 0.625 |
| wellbeing | screen_balance | 0.594 |
| wellbeing | content_quality | 0.250 |
| wellbeing | real_activity | 0.500 |
| wellbeing | sleep | 0.920 |
| wellbeing | family_interaction | 0.650 |

### educational_focused_9yo

- Description: Temps d'écran élevé mais contenu essentiellement éducatif
- Age: 9
- Seed: 105
- Generated events: 182
- addiction_score: 0.152
- wellbeing_score: 0.791
- expected_addiction_range: [0.072, 0.232]
- expected_wellbeing_range: [0.711, 0.871]
- Triggered recommendations: balance_celebration
- Required recommendations: -
- Forbidden recommendations: educational_boost, screen_curfew
- Triggered missions: -
- Expected missions: -
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.072, 0.232] | wellbeing=[0.711, 0.871]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.465 |
| addiction | compulsivity | 0.027 |
| addiction | nocturnal | 0.000 |
| addiction | escalation | 0.000 |
| addiction | imbalance | 0.200 |
| wellbeing | screen_balance | 0.535 |
| wellbeing | content_quality | 0.900 |
| wellbeing | real_activity | 0.700 |
| wellbeing | sleep | 1.000 |
| wellbeing | family_interaction | 0.790 |

### moderate_family_7yo

- Description: Usage modéré avec forte implication familiale
- Age: 7
- Seed: 106
- Generated events: 112
- addiction_score: 0.103
- wellbeing_score: 0.841
- expected_addiction_range: [0.023, 0.183]
- expected_wellbeing_range: [0.761, 0.921]
- Triggered recommendations: balance_celebration
- Required recommendations: balance_celebration
- Forbidden recommendations: daily_limit_reminder, screen_curfew
- Triggered missions: -
- Expected missions: -
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.023, 0.183] | wellbeing=[0.761, 0.921]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.283 |
| addiction | compulsivity | 0.017 |
| addiction | nocturnal | 0.000 |
| addiction | escalation | 0.000 |
| addiction | imbalance | 0.193 |
| wellbeing | screen_balance | 0.717 |
| wellbeing | content_quality | 0.714 |
| wellbeing | real_activity | 0.900 |
| wellbeing | sleep | 1.000 |
| wellbeing | family_interaction | 0.930 |

### weekend_spike_11yo

- Description: Semaine calme, pics d'usage le week-end
- Age: 11
- Seed: 107
- Generated events: 252
- addiction_score: 0.161
- wellbeing_score: 0.670
- expected_addiction_range: [0.081, 0.241]
- expected_wellbeing_range: [0.59, 0.75]
- Triggered recommendations: -
- Required recommendations: -
- Forbidden recommendations: screen_curfew
- Triggered missions: content_quality
- Expected missions: -
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.081, 0.241] | wellbeing=[0.59, 0.75]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.325 |
| addiction | compulsivity | 0.033 |
| addiction | nocturnal | 0.000 |
| addiction | escalation | 0.000 |
| addiction | imbalance | 0.486 |
| wellbeing | screen_balance | 0.675 |
| wellbeing | content_quality | 0.429 |
| wellbeing | real_activity | 0.600 |
| wellbeing | sleep | 1.000 |
| wellbeing | family_interaction | 0.720 |

### social_media_heavy_14yo

- Description: Usage intense d'applications sociales, nombreuses ouvertures courtes
- Age: 14
- Seed: 108
- Generated events: 3094
- addiction_score: 0.451
- wellbeing_score: 0.336
- expected_addiction_range: [0.371, 0.531]
- expected_wellbeing_range: [0.256, 0.416]
- Triggered recommendations: daily_limit_reminder, session_break, imbalance_warning, real_activity_prompt, educational_boost
- Required recommendations: imbalance_warning, session_break
- Forbidden recommendations: balance_celebration
- Triggered missions: content_quality, real_activity
- Expected missions: content_quality, real_activity
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.371, 0.531] | wellbeing=[0.256, 0.416]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.595 |
| addiction | compulsivity | 0.519 |
| addiction | nocturnal | 0.341 |
| addiction | escalation | 0.000 |
| addiction | imbalance | 0.867 |
| wellbeing | screen_balance | 0.405 |
| wellbeing | content_quality | 0.067 |
| wellbeing | real_activity | 0.200 |
| wellbeing | sleep | 0.659 |
| wellbeing | family_interaction | 0.440 |

### post_intervention_recovering_13yo

- Description: Enfant en phase de diminution d'usage après intervention parentale
- Age: 13
- Seed: 109
- Generated events: 336
- addiction_score: 0.187
- wellbeing_score: 0.661
- expected_addiction_range: [0.107, 0.267]
- expected_wellbeing_range: [0.581, 0.741]
- Triggered recommendations: -
- Required recommendations: -
- Forbidden recommendations: balance_celebration, weekly_escalation_alert
- Triggered missions: content_quality
- Expected missions: -
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.107, 0.267] | wellbeing=[0.581, 0.741]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.381 |
| addiction | compulsivity | 0.043 |
| addiction | nocturnal | 0.080 |
| addiction | escalation | 0.000 |
| addiction | imbalance | 0.450 |
| wellbeing | screen_balance | 0.619 |
| wellbeing | content_quality | 0.500 |
| wellbeing | real_activity | 0.600 |
| wellbeing | sleep | 0.920 |
| wellbeing | family_interaction | 0.720 |

### sleep_deprived_10yo

- Description: Usage nocturne marqué impactant le sommeil
- Age: 10
- Seed: 110
- Generated events: 308
- addiction_score: 0.468
- wellbeing_score: 0.295
- expected_addiction_range: [0.388, 0.548]
- expected_wellbeing_range: [0.215, 0.375]
- Triggered recommendations: screen_curfew, daily_limit_reminder, imbalance_warning, educational_boost
- Required recommendations: daily_limit_reminder, screen_curfew
- Forbidden recommendations: balance_celebration
- Triggered missions: nocturnal, sleep
- Expected missions: nocturnal
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.388, 0.548] | wellbeing=[0.215, 0.375]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.659 |
| addiction | compulsivity | 0.041 |
| addiction | nocturnal | 0.835 |
| addiction | escalation | 0.087 |
| addiction | imbalance | 0.736 |
| wellbeing | screen_balance | 0.341 |
| wellbeing | content_quality | 0.229 |
| wellbeing | real_activity | 0.300 |
| wellbeing | sleep | 0.165 |
| wellbeing | family_interaction | 0.510 |

### low_engagement_8yo

- Description: Peu d'écran mais aucun engagement mission/éducatif
- Age: 8
- Seed: 111
- Generated events: 70
- addiction_score: 0.178
- wellbeing_score: 0.443
- expected_addiction_range: [0.098, 0.258]
- expected_wellbeing_range: [0.363, 0.523]
- Triggered recommendations: imbalance_warning, real_activity_prompt
- Required recommendations: real_activity_prompt
- Forbidden recommendations: balance_celebration, screen_curfew
- Triggered missions: real_activity, family_interaction
- Expected missions: real_activity
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.098, 0.258] | wellbeing=[0.363, 0.523]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.136 |
| addiction | compulsivity | 0.010 |
| addiction | nocturnal | 0.000 |
| addiction | escalation | 0.000 |
| addiction | imbalance | 0.950 |
| wellbeing | screen_balance | 0.864 |
| wellbeing | content_quality | 0.100 |
| wellbeing | real_activity | 0.000 |
| wellbeing | sleep | 1.000 |
| wellbeing | family_interaction | 0.300 |

### balanced_teen_16yo

- Description: Adolescent équilibré, usage adapté à la tranche adolescente
- Age: 16
- Seed: 112
- Generated events: 294
- addiction_score: 0.143
- wellbeing_score: 0.747
- expected_addiction_range: [0.063, 0.223]
- expected_wellbeing_range: [0.667, 0.827]
- Triggered recommendations: balance_celebration
- Required recommendations: balance_celebration
- Forbidden recommendations: daily_limit_reminder, screen_curfew
- Triggered missions: -
- Expected missions: -
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.063, 0.223] | wellbeing=[0.667, 0.827]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.341 |
| addiction | compulsivity | 0.036 |
| addiction | nocturnal | 0.000 |
| addiction | escalation | 0.000 |
| addiction | imbalance | 0.338 |
| wellbeing | screen_balance | 0.659 |
| wellbeing | content_quality | 0.625 |
| wellbeing | real_activity | 0.700 |
| wellbeing | sleep | 1.000 |
| wellbeing | family_interaction | 0.790 |

### rising_concern_9yo

- Description: Hausse progressive sans pic aigu
- Age: 9
- Seed: 113
- Generated events: 420
- addiction_score: 0.340
- wellbeing_score: 0.596
- expected_addiction_range: [0.26, 0.42]
- expected_wellbeing_range: [0.516, 0.676]
- Triggered recommendations: weekly_escalation_alert
- Required recommendations: weekly_escalation_alert
- Forbidden recommendations: balance_celebration
- Triggered missions: content_quality, escalation
- Expected missions: escalation
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.26, 0.42] | wellbeing=[0.516, 0.676]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.419 |
| addiction | compulsivity | 0.108 |
| addiction | nocturnal | 0.125 |
| addiction | escalation | 0.539 |
| addiction | imbalance | 0.536 |
| wellbeing | screen_balance | 0.581 |
| wellbeing | content_quality | 0.429 |
| wellbeing | real_activity | 0.500 |
| wellbeing | sleep | 0.875 |
| wellbeing | family_interaction | 0.650 |

### pure_educational_7yo

- Description: Tablette à vocation exclusivement éducative
- Age: 7
- Seed: 114
- Generated events: 70
- addiction_score: 0.056
- wellbeing_score: 0.925
- expected_addiction_range: [0.0, 0.136]
- expected_wellbeing_range: [0.845, 1.0]
- Triggered recommendations: balance_celebration
- Required recommendations: balance_celebration
- Forbidden recommendations: daily_limit_reminder, educational_boost, screen_curfew
- Triggered missions: -
- Expected missions: -
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.0, 0.136] | wellbeing=[0.845, 1.0]

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.171 |
| addiction | compulsivity | 0.014 |
| addiction | nocturnal | 0.000 |
| addiction | escalation | 0.000 |
| addiction | imbalance | 0.070 |
| wellbeing | screen_balance | 0.829 |
| wellbeing | content_quality | 0.960 |
| wellbeing | real_activity | 0.900 |
| wellbeing | sleep | 1.000 |
| wellbeing | family_interaction | 0.930 |

### edge_case_zero_usage

- Description: Aucune donnée d'usage (cas limite)
- Age: 10
- Seed: 115
- Generated events: 0
- addiction_score: 0.150
- wellbeing_score: 0.400
- expected_addiction_range: [0.07, 0.23]
- expected_wellbeing_range: [0.32, 0.48]
- Triggered recommendations: imbalance_warning, real_activity_prompt, family_time_suggestion
- Required recommendations: -
- Forbidden recommendations: balance_celebration, daily_limit_reminder, screen_curfew, session_break, weekly_escalation_alert
- Triggered missions: real_activity, family_interaction
- Expected missions: -
- range_ok: True
- required_ok: True
- forbidden_ok: True
- missions_ok: True

Expected ranges (header): addiction=[0.07, 0.23] | wellbeing=[0.32, 0.48]

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
- Reproduce command: `\.venv\Scripts\python.exe -m evaluation.behavioral.scripts.run_behavioral_benchmark --profiles C:/Users/helmi/OneDrive/Bureau/PFE/AI-Module-to-Turn-Screen-Time-into-Real-Learning-in-a-Parental-Control-App/ai-service/evaluation/behavioral/datasets/behavioral_profiles_v1.json --report-name behavioral_baseline_v2.md`
- Seed list per profile:
| id | seed |
|---|---:|
| balanced_child_8yo | 101 |
| heavy_escalating_12yo | 102 |
| nocturnal_teen_15yo | 103 |
| compulsive_user_10yo | 104 |
| educational_focused_9yo | 105 |
| moderate_family_7yo | 106 |
| weekend_spike_11yo | 107 |
| social_media_heavy_14yo | 108 |
| post_intervention_recovering_13yo | 109 |
| sleep_deprived_10yo | 110 |
| low_engagement_8yo | 111 |
| balanced_teen_16yo | 112 |
| rising_concern_9yo | 113 |
| pure_educational_7yo | 114 |
| edge_case_zero_usage | 115 |

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
