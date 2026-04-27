"""
Behavioral scoring orchestration for AI-07.

Addiction and wellbeing intentionally share a subset of protective signals
(``content_quality_ratio`` and ``mission_completion_rate``), but they are not redundant:

- addiction includes three risk dimensions that are absent from wellbeing:
  intensity, nocturnal usage, and escalation trend;
- wellbeing emphasizes balancing/protective dimensions (screen balance, sleep hygiene,
  family interaction proxy);
- both views are therefore complementary sensitivities over the same behavior window,
  not duplicated outputs.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

from app.contracts.behavioral import (
    BehavioralAnalysisRequest,
    BehavioralAnalysisResponse,
    SubScore,
)
from app.services.behavioral.addiction_scorer import score_addiction
from app.services.behavioral.feature_engineering import (
    content_quality_ratio,
    daily_nocturnal_minutes,
    daily_screen_time_minutes,
    daily_session_count,
    daily_short_session_count,
    daily_unlock_count,
    mission_completion_rate,
    weekly_usage_slope,
)
from app.services.behavioral.mission_engine import generate_missions
from app.services.behavioral.recommendation_engine import generate_recommendations
from app.services.behavioral.wellbeing_scorer import score_wellbeing
from app.services.behavioral.thresholds import ADDICTION_WEIGHTS, WELLBEING_WEIGHTS


def _avg(values: Iterable[float]) -> float:
    values_list = list(values)
    if not values_list:
        return 0.0
    return float(sum(values_list)) / float(len(values_list))


def _resolve_end_date(request: BehavioralAnalysisRequest, computed_at: datetime) -> date:
    if request.events:
        return max(event.started_at.date() for event in request.events)
    return computed_at.date()


def _build_subscore_list(
    order: list[str],
    subscores: dict[str, float],
    feature_values: dict[str, dict[str, float]],
    explanations_fr: dict[str, str],
) -> list[SubScore]:
    result: list[SubScore] = []
    for name in order:
        result.append(
            SubScore.model_validate(
                {
                    "name": name,
                    "value": round(float(subscores[name]), 3),
                    "featureValues": feature_values[name],
                    "explanationFr": explanations_fr[name],
                }
            )
        )
    return result


def score_behavioral_request(
    request: BehavioralAnalysisRequest,
    *,
    computed_at: datetime | None = None,
) -> BehavioralAnalysisResponse:
    """
    Build the full behavioral scoring response from request payload.

    Window aggregation (locked design):
    - daily features are computed per day on ``window_days`` and averaged;
    - ``weekly_usage_slope`` is used as-is;
    - ``content_quality_ratio`` and ``mission_completion_rate`` come directly from summaries.
    """
    computed_at_dt = computed_at or datetime.utcnow()
    window_days = max(1, int(request.window_days))
    end_day = _resolve_end_date(request, computed_at_dt)
    day_list = [end_day - timedelta(days=offset) for offset in range(window_days)]

    events = request.events
    avg_daily_screen_minutes = _avg(daily_screen_time_minutes(events, day) for day in day_list)
    avg_daily_session_count = _avg(float(daily_session_count(events, day)) for day in day_list)
    avg_daily_short_session_count = _avg(
        float(daily_short_session_count(events, day)) for day in day_list
    )
    avg_daily_unlock_count = _avg(float(daily_unlock_count(events, day)) for day in day_list)
    avg_daily_nocturnal_minutes = _avg(daily_nocturnal_minutes(events, day) for day in day_list)

    slope_value = float(weekly_usage_slope(events, end_day))
    content_ratio = float(content_quality_ratio(request.content_analyses_summary))
    mission_rate = float(mission_completion_rate(request.mission_summary))
    mission_assigned = int(request.mission_summary.assigned) if request.mission_summary else 0

    addiction = score_addiction(
        age_years=request.age_years,
        avg_daily_screen_minutes=avg_daily_screen_minutes,
        avg_daily_session_count=avg_daily_session_count,
        avg_daily_short_session_count=avg_daily_short_session_count,
        avg_daily_unlock_count=avg_daily_unlock_count,
        avg_daily_nocturnal_minutes=avg_daily_nocturnal_minutes,
        weekly_usage_slope_value=slope_value,
        content_quality_ratio_value=content_ratio,
        mission_completion_rate_value=mission_rate,
    )
    wellbeing = score_wellbeing(
        age_years=request.age_years,
        avg_daily_screen_minutes=avg_daily_screen_minutes,
        avg_daily_nocturnal_minutes=avg_daily_nocturnal_minutes,
        content_quality_ratio_value=content_ratio,
        mission_completion_rate_value=mission_rate,
        mission_assigned_count=mission_assigned,
    )

    response = BehavioralAnalysisResponse.model_validate(
        {
            "addictionScore": addiction.global_score,
            "addictionSubscores": _build_subscore_list(
                list(ADDICTION_WEIGHTS.keys()),
                addiction.subscores,
                addiction.feature_values,
                addiction.explanations_fr,
            ),
            "wellbeingScore": wellbeing.global_score,
            "wellbeingSubscores": _build_subscore_list(
                list(WELLBEING_WEIGHTS.keys()),
                wellbeing.subscores,
                wellbeing.feature_values,
                wellbeing.explanations_fr,
            ),
            "windowDays": window_days,
            "computedAt": computed_at_dt,
        }
    )
    recommendations = generate_recommendations(response)
    missions = generate_missions(response, request.age_years)
    return response.model_copy(update={"recommendations": recommendations, "missions": missions})
