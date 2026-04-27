# Behavioral Benchmark Report (first-run actuals)

- Run timestamp: **2026-04-24 16:59:14 UTC**
- Profiles file: `C:/Users/helmi/OneDrive/Bureau/PFE/AI-Module-to-Turn-Screen-Time-into-Real-Learning-in-a-Parental-Control-App/ai-service/evaluation/behavioral/datasets/behavioral_profiles_v1.json`
- Total profiles executed: **15**
- Required-recommendation pass rate: **10/15**
- Forbidden-recommendation pass rate: **14/15**

## Recommendation Severity Distribution

| Severity | Count |
|---|---:|
| high | 2 |
| medium | 9 |
| low | 6 |
| positive | 4 |

## Profile Summary Table

| id | age | addiction | wellbeing | triggered | required_ok | forbidden_ok |
|---|---:|---:|---:|---|---|---|
| balanced_child_8yo | 8 | 0.093 | 0.842 | balance_celebration | True | True |
| heavy_escalating_12yo | 12 | 0.349 | 0.488 | imbalance_warning, educational_boost | False | True |
| nocturnal_teen_15yo | 15 | 0.425 | 0.326 | screen_curfew, imbalance_warning, educational_boost | True | True |
| compulsive_user_10yo | 10 | 0.299 | 0.563 | educational_boost | False | True |
| educational_focused_9yo | 9 | 0.152 | 0.791 | balance_celebration | True | False |
| moderate_family_7yo | 7 | 0.103 | 0.841 | balance_celebration | True | True |
| weekend_spike_11yo | 11 | 0.161 | 0.670 | - | True | True |
| social_media_heavy_14yo | 14 | 0.403 | 0.350 | imbalance_warning, real_activity_prompt, educational_boost | False | True |
| post_intervention_recovering_13yo | 13 | 0.187 | 0.661 | - | True | True |
| sleep_deprived_10yo | 10 | 0.468 | 0.295 | screen_curfew, imbalance_warning, educational_boost | True | True |
| low_engagement_8yo | 8 | 0.178 | 0.443 | imbalance_warning, real_activity_prompt | True | True |
| balanced_teen_16yo | 16 | 0.143 | 0.747 | - | False | True |
| rising_concern_9yo | 9 | 0.277 | 0.606 | - | False | True |
| pure_educational_7yo | 7 | 0.056 | 0.925 | balance_celebration | True | True |
| edge_case_zero_usage | 10 | 0.150 | 0.400 | imbalance_warning, real_activity_prompt, family_time_suggestion | True | True |

## Profile Details

### balanced_child_8yo

- Description: Enfant équilibré, 1h d'écran par jour, missions assidues, contenu éducatif
- Age: 8
- Seed: 101
- Generated events: 140
- addiction_score: 0.093
- wellbeing_score: 0.842
- Triggered recommendations: balance_celebration
- Required recommendations: balance_celebration
- Forbidden recommendations: daily_limit_reminder, screen_curfew, session_break, weekly_escalation_alert
- required_ok: True
- forbidden_ok: True

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
- addiction_score: 0.349
- wellbeing_score: 0.488
- Triggered recommendations: imbalance_warning, educational_boost
- Required recommendations: weekly_escalation_alert
- Forbidden recommendations: balance_celebration
- required_ok: False
- forbidden_ok: True

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.400 |
| addiction | compulsivity | 0.119 |
| addiction | nocturnal | 0.154 |
| addiction | escalation | 0.426 |
| addiction | imbalance | 0.725 |
| wellbeing | screen_balance | 0.600 |
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
- Triggered recommendations: screen_curfew, imbalance_warning, educational_boost
- Required recommendations: screen_curfew
- Forbidden recommendations: balance_celebration
- required_ok: True
- forbidden_ok: True

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
- Generated events: 2324
- addiction_score: 0.299
- wellbeing_score: 0.563
- Triggered recommendations: educational_boost
- Required recommendations: session_break
- Forbidden recommendations: balance_celebration
- required_ok: False
- forbidden_ok: True

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.406 |
| addiction | compulsivity | 0.437 |
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
- Triggered recommendations: balance_celebration
- Required recommendations: -
- Forbidden recommendations: balance_celebration, educational_boost, screen_curfew
- required_ok: True
- forbidden_ok: False

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
- Triggered recommendations: balance_celebration
- Required recommendations: balance_celebration
- Forbidden recommendations: daily_limit_reminder, screen_curfew
- required_ok: True
- forbidden_ok: True

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
- Triggered recommendations: -
- Required recommendations: -
- Forbidden recommendations: screen_curfew
- required_ok: True
- forbidden_ok: True

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
- Generated events: 2044
- addiction_score: 0.403
- wellbeing_score: 0.350
- Triggered recommendations: imbalance_warning, real_activity_prompt, educational_boost
- Required recommendations: imbalance_warning, session_break
- Forbidden recommendations: balance_celebration
- required_ok: False
- forbidden_ok: True

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.521 |
| addiction | compulsivity | 0.374 |
| addiction | nocturnal | 0.341 |
| addiction | escalation | 0.000 |
| addiction | imbalance | 0.867 |
| wellbeing | screen_balance | 0.479 |
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
- Triggered recommendations: -
- Required recommendations: -
- Forbidden recommendations: balance_celebration, weekly_escalation_alert
- required_ok: True
- forbidden_ok: True

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
- Triggered recommendations: screen_curfew, imbalance_warning, educational_boost
- Required recommendations: screen_curfew
- Forbidden recommendations: balance_celebration
- required_ok: True
- forbidden_ok: True

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
- Triggered recommendations: imbalance_warning, real_activity_prompt
- Required recommendations: real_activity_prompt
- Forbidden recommendations: balance_celebration, screen_curfew
- required_ok: True
- forbidden_ok: True

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
- Triggered recommendations: -
- Required recommendations: balance_celebration
- Forbidden recommendations: daily_limit_reminder, screen_curfew
- required_ok: False
- forbidden_ok: True

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
- addiction_score: 0.277
- wellbeing_score: 0.606
- Triggered recommendations: -
- Required recommendations: weekly_escalation_alert
- Forbidden recommendations: balance_celebration
- required_ok: False
- forbidden_ok: True

| Subscore group | name | value |
|---|---|---:|
| addiction | intensity | 0.370 |
| addiction | compulsivity | 0.108 |
| addiction | nocturnal | 0.125 |
| addiction | escalation | 0.286 |
| addiction | imbalance | 0.536 |
| wellbeing | screen_balance | 0.630 |
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
- Triggered recommendations: balance_celebration
- Required recommendations: balance_celebration
- Forbidden recommendations: daily_limit_reminder, educational_boost, screen_curfew
- required_ok: True
- forbidden_ok: True

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
- Triggered recommendations: imbalance_warning, real_activity_prompt, family_time_suggestion
- Required recommendations: -
- Forbidden recommendations: balance_celebration, daily_limit_reminder, screen_curfew, session_break, weekly_escalation_alert
- required_ok: True
- forbidden_ok: True

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

## Actuals for Phase 6b Calibration

```json
{
  "balanced_child_8yo": {
    "addiction_score": 0.093,
    "wellbeing_score": 0.842
  },
  "heavy_escalating_12yo": {
    "addiction_score": 0.349,
    "wellbeing_score": 0.488
  },
  "nocturnal_teen_15yo": {
    "addiction_score": 0.425,
    "wellbeing_score": 0.326
  },
  "compulsive_user_10yo": {
    "addiction_score": 0.299,
    "wellbeing_score": 0.563
  },
  "educational_focused_9yo": {
    "addiction_score": 0.152,
    "wellbeing_score": 0.791
  },
  "moderate_family_7yo": {
    "addiction_score": 0.103,
    "wellbeing_score": 0.841
  },
  "weekend_spike_11yo": {
    "addiction_score": 0.161,
    "wellbeing_score": 0.67
  },
  "social_media_heavy_14yo": {
    "addiction_score": 0.403,
    "wellbeing_score": 0.35
  },
  "post_intervention_recovering_13yo": {
    "addiction_score": 0.187,
    "wellbeing_score": 0.661
  },
  "sleep_deprived_10yo": {
    "addiction_score": 0.468,
    "wellbeing_score": 0.295
  },
  "low_engagement_8yo": {
    "addiction_score": 0.178,
    "wellbeing_score": 0.443
  },
  "balanced_teen_16yo": {
    "addiction_score": 0.143,
    "wellbeing_score": 0.747
  },
  "rising_concern_9yo": {
    "addiction_score": 0.277,
    "wellbeing_score": 0.606
  },
  "pure_educational_7yo": {
    "addiction_score": 0.056,
    "wellbeing_score": 0.925
  },
  "edge_case_zero_usage": {
    "addiction_score": 0.15,
    "wellbeing_score": 0.4
  }
}
```
