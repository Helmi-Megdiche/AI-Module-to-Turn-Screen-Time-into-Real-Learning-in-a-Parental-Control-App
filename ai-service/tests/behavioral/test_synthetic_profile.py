"""Unit tests for deterministic synthetic behavioral profile generation."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from evaluation.behavioral.scripts.synthetic_profile import REFERENCE_END_DATE, generate_events


def _base_config() -> dict:
    return {
        "window_days": 14,
        "base_daily_minutes": 90,
        "daily_minutes_growth_per_day": 0.0,
        "sessions_per_day": 3,
        "short_session_fraction": 0.1,
        "unlocks_per_day": 8,
        "nocturnal_minutes_per_day": 0.0,
        "active_hours": [10, 19],
        "weekend_multiplier": 1.0,
    }


def _daily_session_minutes(events: list[dict]) -> dict[date, float]:
    out: dict[date, float] = defaultdict(float)
    for event in events:
        if event.get("eventType") != "app_session":
            continue
        start = datetime.fromisoformat(event["startedAt"])
        out[start.date()] += float(event.get("durationSec", 0)) / 60.0
    return dict(out)


def test_generate_events_is_deterministic() -> None:
    config = _base_config()
    events_a = generate_events(config=config, seed=42, age_years=10)
    events_b = generate_events(config=config, seed=42, age_years=10)
    assert events_a == events_b


def test_generate_events_respects_window_days_date_bounds() -> None:
    config = _base_config()
    events = generate_events(config=config, seed=99, age_years=9)
    earliest = REFERENCE_END_DATE - timedelta(days=13)
    for event in events:
        d = datetime.fromisoformat(event["startedAt"]).date()
        assert earliest <= d <= REFERENCE_END_DATE


def test_growth_parameter_increases_daily_minutes_monotonically() -> None:
    config = _base_config()
    config["daily_minutes_growth_per_day"] = 5.0
    config["sessions_per_day"] = 2
    config["unlocks_per_day"] = 0
    by_day = _daily_session_minutes(generate_events(config=config, seed=1, age_years=12))
    values = [by_day[REFERENCE_END_DATE - timedelta(days=d)] for d in range(13, -1, -1)]
    assert all(curr <= nxt for curr, nxt in zip(values, values[1:]))


def test_weekend_multiplier_increases_weekend_usage() -> None:
    config = _base_config()
    config["sessions_per_day"] = 1
    config["unlocks_per_day"] = 0
    config["short_session_fraction"] = 0.0
    config["weekend_multiplier"] = 3.0
    by_day = _daily_session_minutes(generate_events(config=config, seed=5, age_years=11))
    weekend = [v for d, v in by_day.items() if d.weekday() >= 5]
    weekdays = [v for d, v in by_day.items() if d.weekday() < 5]
    assert weekend
    assert weekdays
    assert sum(weekend) / len(weekend) > sum(weekdays) / len(weekdays)


def test_nocturnal_minutes_adds_one_nocturnal_session_per_day() -> None:
    config = _base_config()
    config["sessions_per_day"] = 0
    config["unlocks_per_day"] = 0
    config["nocturnal_minutes_per_day"] = 45
    events = generate_events(config=config, seed=7, age_years=15)
    nocturnal = [
        e
        for e in events
        if e["eventType"] == "app_session" and 22 <= datetime.fromisoformat(e["startedAt"]).hour <= 23
    ]
    assert len(nocturnal) == config["window_days"]


def test_zero_config_produces_empty_event_list() -> None:
    config = _base_config()
    config.update(
        {
            "base_daily_minutes": 0,
            "sessions_per_day": 0,
            "unlocks_per_day": 0,
            "nocturnal_minutes_per_day": 0,
        }
    )
    events = generate_events(config=config, seed=115, age_years=10)
    assert events == []
