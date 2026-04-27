from __future__ import annotations

from app.services.behavioral.addiction_scorer import score_addiction
from app.services.behavioral.thresholds import ADDICTION_WEIGHTS


def test_addiction_score_keys_and_range():
    result = score_addiction(
        age_years=12,
        avg_daily_screen_minutes=90.0,
        avg_daily_session_count=20.0,
        avg_daily_short_session_count=8.0,
        avg_daily_unlock_count=35.0,
        avg_daily_nocturnal_minutes=10.0,
        weekly_usage_slope_value=0.05,
        content_quality_ratio_value=0.4,
        mission_completion_rate_value=0.5,
    )
    assert set(result.subscores.keys()) == set(ADDICTION_WEIGHTS.keys())
    assert 0.0 <= result.global_score <= 1.0


def test_addiction_higher_risky_inputs_increase_global_score():
    low = score_addiction(
        age_years=12,
        avg_daily_screen_minutes=40.0,
        avg_daily_session_count=8.0,
        avg_daily_short_session_count=1.0,
        avg_daily_unlock_count=10.0,
        avg_daily_nocturnal_minutes=0.0,
        weekly_usage_slope_value=0.0,
        content_quality_ratio_value=0.9,
        mission_completion_rate_value=0.9,
    )
    high = score_addiction(
        age_years=12,
        avg_daily_screen_minutes=260.0,
        avg_daily_session_count=70.0,
        avg_daily_short_session_count=45.0,
        avg_daily_unlock_count=120.0,
        avg_daily_nocturnal_minutes=80.0,
        weekly_usage_slope_value=0.7,
        content_quality_ratio_value=0.1,
        mission_completion_rate_value=0.1,
    )
    assert high.global_score > low.global_score


def test_addiction_escalation_zero_when_slope_negative():
    result = score_addiction(
        age_years=15,
        avg_daily_screen_minutes=140.0,
        avg_daily_session_count=20.0,
        avg_daily_short_session_count=6.0,
        avg_daily_unlock_count=30.0,
        avg_daily_nocturnal_minutes=12.0,
        weekly_usage_slope_value=-0.5,
        content_quality_ratio_value=0.5,
        mission_completion_rate_value=0.5,
    )
    assert result.subscores["escalation"] == 0.0


def test_addiction_compulsivity_sensitive_to_short_ratio():
    low = score_addiction(
        age_years=10,
        avg_daily_screen_minutes=120.0,
        avg_daily_session_count=20.0,
        avg_daily_short_session_count=1.0,
        avg_daily_unlock_count=20.0,
        avg_daily_nocturnal_minutes=5.0,
        weekly_usage_slope_value=0.1,
        content_quality_ratio_value=0.4,
        mission_completion_rate_value=0.5,
    )
    high = score_addiction(
        age_years=10,
        avg_daily_screen_minutes=120.0,
        avg_daily_session_count=20.0,
        avg_daily_short_session_count=15.0,
        avg_daily_unlock_count=20.0,
        avg_daily_nocturnal_minutes=5.0,
        weekly_usage_slope_value=0.1,
        content_quality_ratio_value=0.4,
        mission_completion_rate_value=0.5,
    )
    assert high.subscores["compulsivity"] > low.subscores["compulsivity"]


def test_addiction_imbalance_inverse_of_protective_signals():
    protective = score_addiction(
        age_years=11,
        avg_daily_screen_minutes=100.0,
        avg_daily_session_count=25.0,
        avg_daily_short_session_count=8.0,
        avg_daily_unlock_count=40.0,
        avg_daily_nocturnal_minutes=15.0,
        weekly_usage_slope_value=0.1,
        content_quality_ratio_value=1.0,
        mission_completion_rate_value=1.0,
    )
    weak = score_addiction(
        age_years=11,
        avg_daily_screen_minutes=100.0,
        avg_daily_session_count=25.0,
        avg_daily_short_session_count=8.0,
        avg_daily_unlock_count=40.0,
        avg_daily_nocturnal_minutes=15.0,
        weekly_usage_slope_value=0.1,
        content_quality_ratio_value=0.0,
        mission_completion_rate_value=0.0,
    )
    assert protective.subscores["imbalance"] < weak.subscores["imbalance"]
