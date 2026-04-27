"""Deterministic synthetic behavioral event generator for AI-07 profiles."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import random
from typing import Any


REFERENCE_END_DATE = date(2026, 4, 20)


def _day_minutes_for_index(config: dict[str, Any], day_index: int, day_date: date) -> float:
    base = float(config.get("base_daily_minutes", 0.0))
    growth = float(config.get("daily_minutes_growth_per_day", 0.0))
    value = base + (growth * day_index)
    weekend_multiplier = float(config.get("weekend_multiplier", 1.0))
    if day_date.weekday() >= 5:
        value *= weekend_multiplier
    return max(0.0, value)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def generate_events(config: dict[str, Any], seed: int, age_years: int) -> list[dict[str, Any]]:
    """
    Deterministic synthetic event generation for BehavioralAnalysisRequest payloads.

    Same config + seed => byte-identical event ordering and timestamps.
    """
    _ = age_years  # reserved for future age-aware generator tuning
    rng = random.Random(seed)

    window_days = int(config.get("window_days", 14))
    sessions_per_day = max(0, int(config.get("sessions_per_day", 0)))
    short_fraction = max(0.0, min(1.0, float(config.get("short_session_fraction", 0.0))))
    unlocks_per_day = max(0, int(config.get("unlocks_per_day", 0)))
    nocturnal_minutes_per_day = max(0.0, float(config.get("nocturnal_minutes_per_day", 0.0)))
    active_hours = config.get("active_hours", [10, 19])
    if not isinstance(active_hours, list) or len(active_hours) != 2:
        active_hours = [10, 19]
    active_start = int(active_hours[0])
    active_end = int(active_hours[1])
    if active_end <= active_start:
        active_end = active_start + 1

    events: list[dict[str, Any]] = []
    start_day = REFERENCE_END_DATE - timedelta(days=window_days - 1)

    for day_index in range(window_days):
        day_date = start_day + timedelta(days=day_index)
        day_minutes = _day_minutes_for_index(config, day_index, day_date)

        # App sessions
        if sessions_per_day > 0 and day_minutes > 0.0:
            short_count = int(round(sessions_per_day * short_fraction))
            short_count = min(short_count, sessions_per_day)
            long_count = sessions_per_day - short_count

            durations_sec: list[int] = [rng.randint(10, 29) for _ in range(short_count)]
            remaining_total_sec = max(0, int(day_minutes * 60) - sum(durations_sec))

            if long_count > 0:
                raw_weights = [rng.uniform(0.8, 1.2) for _ in range(long_count)]
                denom = sum(raw_weights) or 1.0
                long_durations = [int(remaining_total_sec * (w / denom)) for w in raw_weights]
                diff = remaining_total_sec - sum(long_durations)
                if long_durations:
                    long_durations[-1] += diff
                durations_sec.extend(max(1, d) for d in long_durations)

            session_start_minutes = sorted(
                rng.randint(active_start * 60, (active_end * 60) - 1)
                for _ in range(len(durations_sec))
            )
            for start_min, duration_sec in zip(session_start_minutes, durations_sec):
                start_dt = datetime(
                    day_date.year, day_date.month, day_date.day, start_min // 60, start_min % 60
                )
                end_dt = start_dt + timedelta(seconds=max(1, duration_sec))
                events.append(
                    {
                        "eventType": "app_session",
                        "appPackage": "com.synthetic.app",
                        "startedAt": _iso(start_dt),
                        "endedAt": _iso(end_dt),
                        "durationSec": int(max(1, duration_sec)),
                    }
                )

        # One nocturnal session per day when configured
        if nocturnal_minutes_per_day > 0.0:
            nocturnal_start = datetime(
                day_date.year,
                day_date.month,
                day_date.day,
                22,
                30,
            ) + timedelta(minutes=rng.randint(0, 60))
            nocturnal_duration = int(nocturnal_minutes_per_day * 60)
            nocturnal_end = nocturnal_start + timedelta(seconds=max(1, nocturnal_duration))
            events.append(
                {
                    "eventType": "app_session",
                    "appPackage": "com.synthetic.app",
                    "startedAt": _iso(nocturnal_start),
                    "endedAt": _iso(nocturnal_end),
                    "durationSec": int(max(1, nocturnal_duration)),
                }
            )

        # Unlock events
        for _ in range(unlocks_per_day):
            unlock_min = rng.randint(active_start * 60, (active_end * 60) - 1)
            unlock_dt = datetime(
                day_date.year, day_date.month, day_date.day, unlock_min // 60, unlock_min % 60
            )
            events.append(
                {
                    "eventType": "unlock",
                    "startedAt": _iso(unlock_dt),
                }
            )

    events.sort(key=lambda e: e["startedAt"])
    return events
