"""Unit tests for ``app.services.behavioral.feature_engineering`` (pure functions)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.services.behavioral.feature_engineering import (
    content_quality_ratio,
    daily_avg_session_length_sec,
    daily_nocturnal_minutes,
    daily_screen_time_minutes,
    daily_session_count,
    daily_short_session_count,
    daily_unlock_count,
    mission_completion_rate,
    weekly_usage_slope,
)


# === Helpers ===


def _session(start: datetime, end: datetime, pkg: str = "com.example.app") -> dict:
    return {
        "event_type": "app_session",
        "app_package": pkg,
        "started_at": start,
        "ended_at": end,
        "duration_sec": int((end - start).total_seconds()),
    }


def _unlock(ts: datetime) -> dict:
    return {
        "event_type": "unlock",
        "app_package": None,
        "started_at": ts,
        "ended_at": None,
        "duration_sec": None,
    }


DAY = date(2026, 4, 20)
DAY_PREV = DAY - timedelta(days=1)
DAY_NEXT = DAY + timedelta(days=1)


def _at(d: date, h: int, m: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, h, m)


# ============================================================
# daily_screen_time_minutes
# ============================================================


def test_screen_time_empty_events():
    assert daily_screen_time_minutes([], DAY) == 0.0


def test_screen_time_single_session_fully_inside_day():
    events = [_session(_at(DAY, 10), _at(DAY, 11))]
    assert daily_screen_time_minutes(events, DAY) == pytest.approx(60.0)


def test_screen_time_multiple_sessions_same_day():
    events = [
        _session(_at(DAY, 9), _at(DAY, 9, 30)),
        _session(_at(DAY, 14), _at(DAY, 15)),
        _session(_at(DAY, 20), _at(DAY, 20, 15)),
    ]
    assert daily_screen_time_minutes(events, DAY) == pytest.approx(30.0 + 60.0 + 15.0)


def test_screen_time_session_crossing_midnight_splits():
    # 23:00 -> 01:30 = 1h before midnight (Monday) + 1.5h after (Tuesday)
    events = [_session(_at(DAY, 23), _at(DAY_NEXT, 1, 30))]
    assert daily_screen_time_minutes(events, DAY) == pytest.approx(60.0)
    assert daily_screen_time_minutes(events, DAY_NEXT) == pytest.approx(90.0)


def test_screen_time_session_entirely_outside_day_ignored():
    events = [_session(_at(DAY_PREV, 10), _at(DAY_PREV, 11))]
    assert daily_screen_time_minutes(events, DAY) == 0.0


def test_screen_time_malformed_events_ignored():
    events = [
        {  # end before start
            "event_type": "app_session",
            "started_at": _at(DAY, 11),
            "ended_at": _at(DAY, 10),
            "duration_sec": None,
        },
        {  # negative duration, no end
            "event_type": "app_session",
            "started_at": _at(DAY, 12),
            "ended_at": None,
            "duration_sec": -100,
        },
        {  # wrong event type
            "event_type": "unlock",
            "started_at": _at(DAY, 13),
            "ended_at": _at(DAY, 14),
            "duration_sec": 3600,
        },
        {  # missing started_at
            "event_type": "app_session",
            "started_at": None,
            "ended_at": _at(DAY, 14),
            "duration_sec": 3600,
        },
        _session(_at(DAY, 15), _at(DAY, 15, 30)),  # valid -> 30 min
    ]
    assert daily_screen_time_minutes(events, DAY) == pytest.approx(30.0)


def test_screen_time_uses_duration_when_end_missing():
    events = [
        {
            "event_type": "app_session",
            "started_at": _at(DAY, 10),
            "ended_at": None,
            "duration_sec": 1800,  # 30 min
        }
    ]
    assert daily_screen_time_minutes(events, DAY) == pytest.approx(30.0)


def test_screen_time_non_int_duration_ignored():
    events = [
        {
            "event_type": "app_session",
            "started_at": _at(DAY, 10),
            "ended_at": None,
            "duration_sec": "not-a-number",
        }
    ]
    assert daily_screen_time_minutes(events, DAY) == 0.0


def test_screen_time_session_with_no_end_and_no_duration_ignored():
    events = [
        {
            "event_type": "app_session",
            "started_at": _at(DAY, 10),
            "ended_at": None,
            "duration_sec": None,
        }
    ]
    assert daily_screen_time_minutes(events, DAY) == 0.0


# ============================================================
# daily_session_count
# ============================================================


def test_session_count_empty():
    assert daily_session_count([], DAY) == 0


def test_session_count_single_session():
    events = [_session(_at(DAY, 10), _at(DAY, 10, 30))]
    assert daily_session_count(events, DAY) == 1


def test_session_count_multiple_sessions_same_day():
    events = [
        _session(_at(DAY, 9), _at(DAY, 9, 5)),
        _session(_at(DAY, 14), _at(DAY, 14, 20)),
        _session(_at(DAY, 22), _at(DAY_NEXT, 0, 5)),  # started on DAY -> counts
    ]
    assert daily_session_count(events, DAY) == 3


def test_session_count_session_started_previous_day_not_counted():
    # Session straddles midnight but started yesterday
    events = [_session(_at(DAY_PREV, 23), _at(DAY, 0, 30))]
    assert daily_session_count(events, DAY) == 0
    assert daily_session_count(events, DAY_PREV) == 1


def test_session_count_malformed_ignored():
    events = [
        {
            "event_type": "app_session",
            "started_at": _at(DAY, 10),
            "ended_at": _at(DAY, 9),  # invalid
            "duration_sec": None,
        },
        _unlock(_at(DAY, 10)),  # wrong type
    ]
    assert daily_session_count(events, DAY) == 0


# ============================================================
# daily_avg_session_length_sec
# ============================================================


def test_avg_session_length_empty():
    assert daily_avg_session_length_sec([], DAY) == 0.0


def test_avg_session_length_single_session():
    events = [_session(_at(DAY, 10), _at(DAY, 10, 2))]  # 120 s
    assert daily_avg_session_length_sec(events, DAY) == pytest.approx(120.0)


def test_avg_session_length_multiple_sessions():
    events = [
        _session(_at(DAY, 10), _at(DAY, 10, 1)),  # 60
        _session(_at(DAY, 12), _at(DAY, 12, 3)),  # 180
        _session(_at(DAY, 14), _at(DAY, 14, 2)),  # 120
    ]
    assert daily_avg_session_length_sec(events, DAY) == pytest.approx(120.0)


def test_avg_session_length_other_day_excluded():
    events = [
        _session(_at(DAY, 10), _at(DAY, 10, 1)),  # 60 s on DAY
        _session(_at(DAY_NEXT, 10), _at(DAY_NEXT, 10, 10)),  # 600 s on next day
    ]
    assert daily_avg_session_length_sec(events, DAY) == pytest.approx(60.0)


def test_avg_session_length_ignores_malformed():
    events = [
        _session(_at(DAY, 10), _at(DAY, 10, 2)),  # valid 120s
        {
            "event_type": "app_session",
            "started_at": _at(DAY, 12),
            "ended_at": _at(DAY, 11),
            "duration_sec": None,
        },
    ]
    assert daily_avg_session_length_sec(events, DAY) == pytest.approx(120.0)


# ============================================================
# daily_short_session_count
# ============================================================


def test_short_session_count_empty():
    assert daily_short_session_count([], DAY) == 0


def test_short_session_count_single_short():
    events = [_session(_at(DAY, 10), _at(DAY, 10) + timedelta(seconds=20))]
    assert daily_short_session_count(events, DAY) == 1


def test_short_session_count_mix_short_and_long():
    events = [
        _session(_at(DAY, 9), _at(DAY, 9) + timedelta(seconds=10)),  # short
        _session(_at(DAY, 10), _at(DAY, 10) + timedelta(seconds=25)),  # short
        _session(_at(DAY, 11), _at(DAY, 11) + timedelta(seconds=60)),  # long
    ]
    assert daily_short_session_count(events, DAY) == 2


def test_short_session_count_custom_threshold():
    events = [_session(_at(DAY, 10), _at(DAY, 10) + timedelta(seconds=90))]
    assert daily_short_session_count(events, DAY, short_threshold_sec=120) == 1
    assert daily_short_session_count(events, DAY, short_threshold_sec=60) == 0


def test_short_session_count_other_day_excluded():
    events = [
        _session(_at(DAY_NEXT, 10), _at(DAY_NEXT, 10) + timedelta(seconds=10))
    ]
    assert daily_short_session_count(events, DAY) == 0


def test_short_session_count_malformed_ignored():
    events = [
        {
            "event_type": "app_session",
            "started_at": _at(DAY, 10),
            "ended_at": None,
            "duration_sec": -5,
        }
    ]
    assert daily_short_session_count(events, DAY) == 0


# ============================================================
# daily_unlock_count
# ============================================================


def test_unlock_count_empty():
    assert daily_unlock_count([], DAY) == 0


def test_unlock_count_single_unlock():
    assert daily_unlock_count([_unlock(_at(DAY, 8))], DAY) == 1


def test_unlock_count_multiple_unlocks():
    events = [_unlock(_at(DAY, 8)), _unlock(_at(DAY, 12)), _unlock(_at(DAY, 20))]
    assert daily_unlock_count(events, DAY) == 3


def test_unlock_count_wrong_day_excluded():
    events = [_unlock(_at(DAY_PREV, 23)), _unlock(_at(DAY_NEXT, 0))]
    assert daily_unlock_count(events, DAY) == 0


def test_unlock_count_ignores_non_unlock_events():
    events = [_session(_at(DAY, 10), _at(DAY, 10, 5)), _unlock(_at(DAY, 9))]
    assert daily_unlock_count(events, DAY) == 1


def test_unlock_count_ignores_bad_timestamp():
    events = [{"event_type": "unlock", "started_at": "not-a-datetime"}]
    assert daily_unlock_count(events, DAY) == 0


# ============================================================
# daily_nocturnal_minutes
# ============================================================


def test_nocturnal_empty_events():
    assert daily_nocturnal_minutes([], DAY) == 0.0


def test_nocturnal_single_evening_session():
    # 22:30 -> 23:30 entirely inside evening nocturnal half
    events = [_session(_at(DAY, 22, 30), _at(DAY, 23, 30))]
    assert daily_nocturnal_minutes(events, DAY) == pytest.approx(60.0)


def test_nocturnal_single_morning_session():
    # 05:00 -> 06:30 inside morning nocturnal half [00:00, 07:00)
    events = [_session(_at(DAY, 5), _at(DAY, 6, 30))]
    assert daily_nocturnal_minutes(events, DAY) == pytest.approx(90.0)


def test_nocturnal_daytime_session_excluded():
    events = [_session(_at(DAY, 10), _at(DAY, 12))]
    assert daily_nocturnal_minutes(events, DAY) == 0.0


def test_nocturnal_midnight_crossing_splits_across_two_days():
    # 23:00 Mon -> 01:30 Tue: 60 min evening on DAY + 90 min morning on DAY+1
    events = [_session(_at(DAY, 23), _at(DAY_NEXT, 1, 30))]
    assert daily_nocturnal_minutes(events, DAY) == pytest.approx(60.0)
    assert daily_nocturnal_minutes(events, DAY_NEXT) == pytest.approx(90.0)


def test_nocturnal_custom_hours():
    # Restrict window to [00:00, 06:00) morning + [23:00, 24:00) evening
    events = [_session(_at(DAY, 23, 30), _at(DAY_NEXT, 0, 0))]
    assert daily_nocturnal_minutes(events, DAY, start_hour=23, end_hour=6) == pytest.approx(30.0)


def test_nocturnal_invalid_hours_return_zero():
    events = [_session(_at(DAY, 23), _at(DAY_NEXT, 1))]
    assert daily_nocturnal_minutes(events, DAY, start_hour=25, end_hour=7) == 0.0
    assert daily_nocturnal_minutes(events, DAY, start_hour=22, end_hour=-1) == 0.0


def test_nocturnal_malformed_events_ignored():
    events = [
        {
            "event_type": "app_session",
            "started_at": _at(DAY, 23),
            "ended_at": _at(DAY, 22),  # invalid
            "duration_sec": None,
        }
    ]
    assert daily_nocturnal_minutes(events, DAY) == 0.0


# ============================================================
# weekly_usage_slope
# ============================================================


def test_slope_empty_returns_zero():
    assert weekly_usage_slope([], DAY) == 0.0


def test_slope_flat_usage_returns_zero():
    # 1h session each day for last 14 days -> equal -> slope 0
    events = []
    for offset in range(14):
        d = DAY - timedelta(days=offset)
        events.append(_session(_at(d, 10), _at(d, 11)))
    assert weekly_usage_slope(events, DAY) == pytest.approx(0.0)


def test_slope_doubling_usage_returns_one():
    events = []
    # Previous week: 30 min/day
    for offset in range(7, 14):
        d = DAY - timedelta(days=offset)
        events.append(_session(_at(d, 10), _at(d, 10, 30)))
    # Current week: 60 min/day
    for offset in range(0, 7):
        d = DAY - timedelta(days=offset)
        events.append(_session(_at(d, 10), _at(d, 11)))
    assert weekly_usage_slope(events, DAY) == pytest.approx(1.0)


def test_slope_previous_zero_current_positive_returns_zero():
    events = [_session(_at(DAY, 10), _at(DAY, 11))]
    # Insufficient history (no previous-week usage): conservative no-trend output.
    assert weekly_usage_slope(events, DAY) == 0.0


def test_slope_true_escalation_detected_with_two_weeks_history():
    events = []
    # Week -2 total = 300 min (42.857 min/day)
    for offset in range(7, 14):
        d = DAY - timedelta(days=offset)
        events.append(_session(_at(d, 10), _at(d, 10) + timedelta(minutes=300 / 7)))
    # Week -1 total = 600 min (85.714 min/day)
    for offset in range(0, 7):
        d = DAY - timedelta(days=offset)
        events.append(_session(_at(d, 10), _at(d, 10) + timedelta(minutes=600 / 7)))
    assert weekly_usage_slope(events, DAY) == pytest.approx(1.0, rel=1e-6)


def test_slope_decrease_is_negative():
    events = []
    # Previous week: 60 min/day
    for offset in range(7, 14):
        d = DAY - timedelta(days=offset)
        events.append(_session(_at(d, 10), _at(d, 11)))
    # Current week: 30 min/day
    for offset in range(0, 7):
        d = DAY - timedelta(days=offset)
        events.append(_session(_at(d, 10), _at(d, 10, 30)))
    assert weekly_usage_slope(events, DAY) == pytest.approx(-0.5)


def test_slope_malformed_events_ignored():
    events = [
        {
            "event_type": "app_session",
            "started_at": _at(DAY, 10),
            "ended_at": _at(DAY, 9),  # invalid
            "duration_sec": None,
        }
    ]
    assert weekly_usage_slope(events, DAY) == 0.0


# ============================================================
# content_quality_ratio
# ============================================================


def test_content_quality_ratio_none():
    assert content_quality_ratio(None) == 0.0


def test_content_quality_ratio_empty_dict():
    assert content_quality_ratio({}) == 0.0


def test_content_quality_ratio_zero_total():
    summary = {"educational_count": 0, "risky_count": 0, "dangerous_count": 0, "total": 0}
    assert content_quality_ratio(summary) == 0.0


def test_content_quality_ratio_half_educational():
    summary = {"educational_count": 5, "risky_count": 3, "dangerous_count": 2, "total": 10}
    assert content_quality_ratio(summary) == pytest.approx(0.5)


def test_content_quality_ratio_all_educational():
    summary = {"educational_count": 7, "total": 7}
    assert content_quality_ratio(summary) == 1.0


def test_content_quality_ratio_negative_educational_returns_zero():
    summary = {"educational_count": -1, "total": 5}
    assert content_quality_ratio(summary) == 0.0


def test_content_quality_ratio_non_numeric_returns_zero():
    summary = {"educational_count": "abc", "total": 10}
    assert content_quality_ratio(summary) == 0.0


def test_content_quality_ratio_accepts_object_like():
    class Summary:
        educational_count = 2
        total = 8

    assert content_quality_ratio(Summary()) == pytest.approx(0.25)


# ============================================================
# mission_completion_rate
# ============================================================


def test_mission_completion_rate_none():
    assert mission_completion_rate(None) == 0.0


def test_mission_completion_rate_zero_assigned():
    assert mission_completion_rate({"completed": 0, "assigned": 0}) == 0.0


def test_mission_completion_rate_full_completion():
    assert mission_completion_rate({"completed": 4, "assigned": 4}) == 1.0


def test_mission_completion_rate_partial_completion():
    assert mission_completion_rate({"completed": 3, "assigned": 10}) == pytest.approx(0.3)


def test_mission_completion_rate_completed_greater_than_assigned_is_clamped():
    # Defensive clamp: in case of bad upstream data, never return > 1.0
    assert mission_completion_rate({"completed": 20, "assigned": 10}) == 1.0


def test_mission_completion_rate_negative_completed_returns_zero():
    assert mission_completion_rate({"completed": -2, "assigned": 5}) == 0.0


def test_mission_completion_rate_accepts_object_like():
    class Mission:
        completed = 3
        assigned = 6

    assert mission_completion_rate(Mission()) == pytest.approx(0.5)


def test_mission_completion_rate_non_numeric_returns_zero():
    assert mission_completion_rate({"completed": "x", "assigned": 5}) == 0.0
