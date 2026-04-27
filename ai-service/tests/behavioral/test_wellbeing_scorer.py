from __future__ import annotations

import pytest

from app.services.behavioral.thresholds import WELLBEING_WEIGHTS
from app.services.behavioral.wellbeing_scorer import score_wellbeing


def test_wellbeing_score_keys_and_range():
    result = score_wellbeing(
        age_years=12,
        avg_daily_screen_minutes=80.0,
        avg_daily_nocturnal_minutes=10.0,
        content_quality_ratio_value=0.6,
        mission_completion_rate_value=0.5,
        mission_assigned_count=3,
    )
    assert set(result.subscores.keys()) == set(WELLBEING_WEIGHTS.keys())
    assert 0.0 <= result.global_score <= 1.0


def test_wellbeing_better_inputs_raise_score():
    low = score_wellbeing(
        age_years=12,
        avg_daily_screen_minutes=260.0,
        avg_daily_nocturnal_minutes=90.0,
        content_quality_ratio_value=0.05,
        mission_completion_rate_value=0.1,
        mission_assigned_count=1,
    )
    high = score_wellbeing(
        age_years=12,
        avg_daily_screen_minutes=70.0,
        avg_daily_nocturnal_minutes=0.0,
        content_quality_ratio_value=0.9,
        mission_completion_rate_value=0.9,
        mission_assigned_count=6,
    )
    assert high.global_score > low.global_score


def test_family_interaction_formula_locked():
    result = score_wellbeing(
        age_years=13,
        avg_daily_screen_minutes=90.0,
        avg_daily_nocturnal_minutes=8.0,
        content_quality_ratio_value=0.5,
        mission_completion_rate_value=0.6,
        mission_assigned_count=3,
    )
    fv = result.feature_values["family_interaction"]
    expected = 0.7 * 0.6 + 0.3 * min(1.0, 3 / 5.0)
    assert fv["formula"] == pytest.approx(expected)
    assert result.subscores["family_interaction"] == pytest.approx(expected)


def test_family_interaction_assigned_cap_at_five():
    result = score_wellbeing(
        age_years=13,
        avg_daily_screen_minutes=90.0,
        avg_daily_nocturnal_minutes=8.0,
        content_quality_ratio_value=0.5,
        mission_completion_rate_value=0.2,
        mission_assigned_count=50,
    )
    expected = 0.7 * 0.2 + 0.3 * 1.0
    assert result.subscores["family_interaction"] == pytest.approx(expected)


def test_sleep_subscore_improves_with_less_nocturnal_usage():
    high_nocturnal = score_wellbeing(
        age_years=14,
        avg_daily_screen_minutes=120.0,
        avg_daily_nocturnal_minutes=50.0,
        content_quality_ratio_value=0.5,
        mission_completion_rate_value=0.5,
        mission_assigned_count=4,
    )
    low_nocturnal = score_wellbeing(
        age_years=14,
        avg_daily_screen_minutes=120.0,
        avg_daily_nocturnal_minutes=2.0,
        content_quality_ratio_value=0.5,
        mission_completion_rate_value=0.5,
        mission_assigned_count=4,
    )
    assert low_nocturnal.subscores["sleep"] > high_nocturnal.subscores["sleep"]


def test_real_activity_tracks_mission_completion_rate():
    low = score_wellbeing(
        age_years=11,
        avg_daily_screen_minutes=110.0,
        avg_daily_nocturnal_minutes=5.0,
        content_quality_ratio_value=0.5,
        mission_completion_rate_value=0.2,
        mission_assigned_count=5,
    )
    high = score_wellbeing(
        age_years=11,
        avg_daily_screen_minutes=110.0,
        avg_daily_nocturnal_minutes=5.0,
        content_quality_ratio_value=0.5,
        mission_completion_rate_value=0.9,
        mission_assigned_count=5,
    )
    assert low.subscores["real_activity"] == pytest.approx(0.2)
    assert high.subscores["real_activity"] == pytest.approx(0.9)
