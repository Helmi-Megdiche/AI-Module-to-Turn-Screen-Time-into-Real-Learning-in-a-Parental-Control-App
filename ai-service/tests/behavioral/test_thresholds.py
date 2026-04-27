"""Unit tests for ``app.services.behavioral.thresholds``."""

from __future__ import annotations

import math

from app.services.behavioral.thresholds import (
    ADDICTION_WEIGHTS,
    AGE_SCREEN_TIME_MAX_MINUTES,
    COMPULSIVITY_SESSION_COUNT_THRESHOLD,
    COMPULSIVITY_SHORT_SESSION_SEC,
    ESCALATION_WEEKLY_SLOPE_THRESHOLD,
    NOCTURNAL_CRITICAL_MINUTES,
    NOCTURNAL_WINDOW_END_HOUR,
    NOCTURNAL_WINDOW_START_HOUR,
    WELLBEING_WEIGHTS,
    get_age_screen_threshold,
)


# === get_age_screen_threshold: age-bracket boundaries ===


def test_get_age_screen_threshold_toddler_lower_bound():
    assert get_age_screen_threshold(2) == 60


def test_get_age_screen_threshold_toddler_upper_bound():
    assert get_age_screen_threshold(5) == 60


def test_get_age_screen_threshold_child_lower_bound():
    assert get_age_screen_threshold(6) == 120


def test_get_age_screen_threshold_child_upper_bound():
    assert get_age_screen_threshold(12) == 120


def test_get_age_screen_threshold_teen_lower_bound():
    assert get_age_screen_threshold(13) == 180


def test_get_age_screen_threshold_teen_upper_bound():
    assert get_age_screen_threshold(18) == 180


# === get_age_screen_threshold: out-of-bracket behavior ===


def test_get_age_screen_threshold_under_two_returns_zero():
    assert get_age_screen_threshold(1) == 0


def test_get_age_screen_threshold_negative_age_returns_zero():
    assert get_age_screen_threshold(-3) == 0


def test_get_age_screen_threshold_adult_falls_back_to_adolescent():
    assert get_age_screen_threshold(20) == 180


# === Weight dictionaries sum to 1.0 ===


def test_addiction_weights_sum_to_one():
    assert math.isclose(sum(ADDICTION_WEIGHTS.values()), 1.0, abs_tol=1e-9)


def test_wellbeing_weights_sum_to_one():
    assert math.isclose(sum(WELLBEING_WEIGHTS.values()), 1.0, abs_tol=1e-9)


def test_addiction_weights_have_five_subscores():
    assert len(ADDICTION_WEIGHTS) == 5


def test_wellbeing_weights_have_five_subscores():
    assert len(WELLBEING_WEIGHTS) == 5


# === Constants sanity ===


def test_nocturnal_window_hours_are_reasonable():
    assert 0 <= NOCTURNAL_WINDOW_END_HOUR < NOCTURNAL_WINDOW_START_HOUR <= 23


def test_compulsivity_thresholds_are_positive():
    assert COMPULSIVITY_SESSION_COUNT_THRESHOLD > 0
    assert COMPULSIVITY_SHORT_SESSION_SEC > 0


def test_escalation_slope_threshold_is_positive_fraction():
    assert 0.0 < ESCALATION_WEEKLY_SLOPE_THRESHOLD < 1.0


def test_nocturnal_critical_minutes_positive():
    assert NOCTURNAL_CRITICAL_MINUTES > 0


def test_age_brackets_dict_exposed():
    assert (2, 5) in AGE_SCREEN_TIME_MAX_MINUTES
    assert (6, 12) in AGE_SCREEN_TIME_MAX_MINUTES
    assert (13, 18) in AGE_SCREEN_TIME_MAX_MINUTES
