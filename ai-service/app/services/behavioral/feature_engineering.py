"""
Pure, stateless feature extraction for behavioral usage events.

All functions operate on plain Python inputs (``list``/``dict``/``datetime``) and never
touch I/O, DB, or logging — this keeps them trivially testable and deterministic.
Inputs can be either plain dicts (snake_case keys matching
``app.contracts.behavioral.UsageEventPayload``) or duck-typed objects exposing the same
attributes (e.g. Pydantic models). Malformed events are silently skipped rather than
raising: upstream validation (Pydantic / Node backend) is expected to have done strict
type enforcement; this layer stays defensive.

Conventions
-----------
- "Screen time" for a calendar day = overlap in minutes between session intervals and
  the day window ``[date 00:00, date+1 00:00)``. Sessions crossing midnight are split.
- "Session count", "short session count", "avg session length" are grouped by
  ``started_at.date()`` (the day a session belongs to its start). This avoids
  double-counting long sessions.
- "Nocturnal minutes for date D" = overlap with ``[D 00:00, D 07:00)`` **plus**
  ``[D 22:00, D+1 00:00)`` (both morning and evening night halves).
- "Unlock count" counts events of type ``unlock`` whose ``started_at.date() == D``.
- "Weekly slope" returns ``0.0`` when the previous week has no data (insufficient
  history: no trend inference for fresh users).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from typing import Any, Optional


# === Internal accessors (dict-or-object duck typing) ===


def _get(event: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a dict or the same attribute from an object."""
    if isinstance(event, dict):
        return event.get(key, default)
    return getattr(event, key, default)


def _as_datetime(value: Any) -> Optional[datetime]:
    """Return ``value`` iff it is already a ``datetime`` (no string parsing here)."""
    return value if isinstance(value, datetime) else None


def _session_bounds(event: Any) -> Optional[tuple[datetime, datetime]]:
    """
    Extract ``(started_at, ended_at)`` for an ``app_session`` event, or ``None`` if
    the event is malformed / not a session.

    A session is well-formed when it has a ``datetime`` ``started_at`` and either
    a ``datetime`` ``ended_at`` (not before start) or a non-negative
    ``duration_sec``. Any other combination is treated as invalid and skipped.
    """
    if _get(event, "event_type") != "app_session":
        return None
    started_at = _as_datetime(_get(event, "started_at"))
    if started_at is None:
        return None

    ended_at = _as_datetime(_get(event, "ended_at"))
    if ended_at is not None:
        if ended_at < started_at:
            return None
        return started_at, ended_at

    duration_sec = _get(event, "duration_sec")
    if duration_sec is None:
        return None
    try:
        duration_int = int(duration_sec)
    except (TypeError, ValueError):
        return None
    if duration_int < 0:
        return None
    return started_at, started_at + timedelta(seconds=duration_int)


def _overlap_seconds(
    start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime
) -> float:
    """Seconds of overlap between two half-open intervals ``[a_start, a_end)``."""
    lo = max(start_a, start_b)
    hi = min(end_a, end_b)
    if hi <= lo:
        return 0.0
    return (hi - lo).total_seconds()


def _day_window(target_date: date) -> tuple[datetime, datetime]:
    """Half-open day window ``[date 00:00, date+1 00:00)``."""
    start = datetime.combine(target_date, time.min)
    return start, start + timedelta(days=1)


# === Public feature functions ===


def daily_screen_time_minutes(events: Iterable[Any], target_date: date) -> float:
    """
    Total minutes spent inside app sessions on ``target_date``.

    Sessions crossing midnight contribute only the portion that falls inside the day.
    Invalid events are ignored.
    """
    day_start, day_end = _day_window(target_date)
    total_seconds = 0.0
    for event in events:
        bounds = _session_bounds(event)
        if bounds is None:
            continue
        started_at, ended_at = bounds
        total_seconds += _overlap_seconds(started_at, ended_at, day_start, day_end)
    return total_seconds / 60.0


def daily_session_count(events: Iterable[Any], target_date: date) -> int:
    """Number of valid ``app_session`` events whose ``started_at`` falls on ``target_date``."""
    count = 0
    for event in events:
        bounds = _session_bounds(event)
        if bounds is None:
            continue
        started_at, _ = bounds
        if started_at.date() == target_date:
            count += 1
    return count


def daily_avg_session_length_sec(events: Iterable[Any], target_date: date) -> float:
    """
    Average session duration (seconds) among sessions started on ``target_date``.

    Returns ``0.0`` when no valid session started that day.
    """
    total_seconds = 0.0
    session_count = 0
    for event in events:
        bounds = _session_bounds(event)
        if bounds is None:
            continue
        started_at, ended_at = bounds
        if started_at.date() != target_date:
            continue
        total_seconds += (ended_at - started_at).total_seconds()
        session_count += 1
    if session_count == 0:
        return 0.0
    return total_seconds / session_count


def daily_short_session_count(
    events: Iterable[Any],
    target_date: date,
    short_threshold_sec: int = 30,
) -> int:
    """Count sessions started on ``target_date`` with duration ``< short_threshold_sec``."""
    count = 0
    for event in events:
        bounds = _session_bounds(event)
        if bounds is None:
            continue
        started_at, ended_at = bounds
        if started_at.date() != target_date:
            continue
        duration = (ended_at - started_at).total_seconds()
        if duration < short_threshold_sec:
            count += 1
    return count


def daily_unlock_count(events: Iterable[Any], target_date: date) -> int:
    """Number of ``unlock`` events whose ``started_at`` falls on ``target_date``."""
    count = 0
    for event in events:
        if _get(event, "event_type") != "unlock":
            continue
        started_at = _as_datetime(_get(event, "started_at"))
        if started_at is None:
            continue
        if started_at.date() == target_date:
            count += 1
    return count


def daily_nocturnal_minutes(
    events: Iterable[Any],
    target_date: date,
    start_hour: int = 22,
    end_hour: int = 7,
) -> float:
    """
    Minutes of app-session usage during the nocturnal window of ``target_date``.

    The nocturnal window for date ``D`` is the union of the morning half
    ``[D 00:00, D end_hour:00)`` and the evening half ``[D start_hour:00, D+1 00:00)``.
    A session crossing midnight is therefore counted proportionally on both days
    (evening portion on ``D``, morning portion on ``D+1``).
    """
    if not 0 <= start_hour <= 23 or not 0 <= end_hour <= 23:
        return 0.0

    day_start = datetime.combine(target_date, time.min)
    night_morning_start = day_start
    night_morning_end = datetime.combine(target_date, time(hour=end_hour))
    night_evening_start = datetime.combine(target_date, time(hour=start_hour))
    night_evening_end = day_start + timedelta(days=1)

    total_seconds = 0.0
    for event in events:
        bounds = _session_bounds(event)
        if bounds is None:
            continue
        started_at, ended_at = bounds
        total_seconds += _overlap_seconds(
            started_at, ended_at, night_morning_start, night_morning_end
        )
        total_seconds += _overlap_seconds(
            started_at, ended_at, night_evening_start, night_evening_end
        )
    return total_seconds / 60.0


def weekly_usage_slope(events: Iterable[Any], end_date: date) -> float:
    """
    Week-over-week growth rate of daily screen time.

    Compares the 7-day window ending at ``end_date`` (inclusive) against the
    preceding 7-day window. Returns ``(current - previous) / previous``. Edge
    cases:

    - Both windows zero → ``0.0`` (flat, no data).
    - Previous zero, current positive → ``0.0`` (insufficient history, cannot
      assess trend; use a dedicated "new user" signal upstream if needed).
    """
    event_list = list(events)

    def _week_total(window_end: date) -> float:
        total = 0.0
        for offset in range(7):
            d = window_end - timedelta(days=offset)
            total += daily_screen_time_minutes(event_list, d)
        return total

    current_total = _week_total(end_date)
    previous_total = _week_total(end_date - timedelta(days=7))

    if previous_total <= 0.0:
        return 0.0
    return (current_total - previous_total) / previous_total


def content_quality_ratio(content_summary: Optional[Any]) -> float:
    """
    Ratio of educational screenshots over the total moderated count.

    Accepts a dict or any object exposing ``educational_count`` and ``total``.
    Returns ``0.0`` for ``None``, missing fields, or a zero/negative total.
    """
    if content_summary is None:
        return 0.0
    educational = _get(content_summary, "educational_count", 0) or 0
    total = _get(content_summary, "total", 0) or 0
    try:
        educational = int(educational)
        total = int(total)
    except (TypeError, ValueError):
        return 0.0
    if total <= 0 or educational < 0:
        return 0.0
    ratio = educational / total
    return max(0.0, min(1.0, ratio))


def mission_completion_rate(mission_summary: Optional[Any]) -> float:
    """
    Share of assigned missions that were completed.

    Accepts a dict or any object exposing ``completed`` and ``assigned``.
    Returns ``0.0`` for ``None``, missing fields, or a zero/negative ``assigned``.
    """
    if mission_summary is None:
        return 0.0
    completed = _get(mission_summary, "completed", 0) or 0
    assigned = _get(mission_summary, "assigned", 0) or 0
    try:
        completed = int(completed)
        assigned = int(assigned)
    except (TypeError, ValueError):
        return 0.0
    if assigned <= 0 or completed < 0:
        return 0.0
    rate = completed / assigned
    return max(0.0, min(1.0, rate))
