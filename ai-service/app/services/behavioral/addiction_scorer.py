from __future__ import annotations

from dataclasses import dataclass

from app.services.behavioral.scoring_utils import saturating_score, weighted_global
from app.services.behavioral.thresholds import (
    ADDICTION_WEIGHTS,
    COMPULSIVITY_SESSION_COUNT_THRESHOLD,
    ESCALATION_WEEKLY_SLOPE_THRESHOLD,
    NOCTURNAL_CRITICAL_MINUTES,
    get_age_screen_threshold,
)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class ScoringBundle:
    global_score: float
    subscores: dict[str, float]
    feature_values: dict[str, dict[str, float]]
    explanations_fr: dict[str, str]


def score_addiction(
    *,
    age_years: int,
    avg_daily_screen_minutes: float,
    avg_daily_session_count: float,
    avg_daily_short_session_count: float,
    avg_daily_unlock_count: float,
    avg_daily_nocturnal_minutes: float,
    weekly_usage_slope_value: float,
    content_quality_ratio_value: float = 0.0,
    mission_completion_rate_value: float = 0.0,
) -> ScoringBundle:
    """
    Compute addiction score + five explainable subscores.

    The scorer is pure and deterministic. It combines clinical thresholds with smooth
    saturation curves to avoid brittle step changes.
    """
    age_threshold_min = float(get_age_screen_threshold(age_years))
    session_count_safe = max(1.0, float(avg_daily_session_count))

    intensity = saturating_score(avg_daily_screen_minutes, age_threshold_min)

    session_freq_harm = saturating_score(
        avg_daily_session_count,
        float(COMPULSIVITY_SESSION_COUNT_THRESHOLD),
    )
    short_ratio = _clamp01(avg_daily_short_session_count / session_count_safe)
    short_ratio_harm = saturating_score(short_ratio, inflection=0.5)
    unlock_harm = saturating_score(avg_daily_unlock_count, inflection=80.0)
    compulsivity = _clamp01(0.5 * session_freq_harm + 0.3 * short_ratio_harm + 0.2 * unlock_harm)

    nocturnal = saturating_score(avg_daily_nocturnal_minutes, float(NOCTURNAL_CRITICAL_MINUTES))

    positive_slope = max(0.0, float(weekly_usage_slope_value))
    escalation = saturating_score(positive_slope, float(ESCALATION_WEEKLY_SLOPE_THRESHOLD))

    protective_index = _clamp01(
        0.5 * float(content_quality_ratio_value) + 0.5 * float(mission_completion_rate_value)
    )
    imbalance = 1.0 - protective_index

    subscores = {
        "intensity": _clamp01(intensity),
        "compulsivity": _clamp01(compulsivity),
        "nocturnal": _clamp01(nocturnal),
        "escalation": _clamp01(escalation),
        "imbalance": _clamp01(imbalance),
    }
    feature_values = {
        "intensity": {
            "avg_daily_screen_minutes": float(avg_daily_screen_minutes),
            "age_threshold_minutes": age_threshold_min,
        },
        "compulsivity": {
            "avg_daily_session_count": float(avg_daily_session_count),
            "avg_daily_short_session_count": float(avg_daily_short_session_count),
            "short_session_ratio": short_ratio,
            "avg_daily_unlock_count": float(avg_daily_unlock_count),
        },
        "nocturnal": {
            "avg_daily_nocturnal_minutes": float(avg_daily_nocturnal_minutes),
            "critical_nocturnal_minutes": float(NOCTURNAL_CRITICAL_MINUTES),
        },
        "escalation": {
            "weekly_usage_slope": float(weekly_usage_slope_value),
            "slope_threshold": float(ESCALATION_WEEKLY_SLOPE_THRESHOLD),
        },
        "imbalance": {
            "content_quality_ratio": _clamp01(float(content_quality_ratio_value)),
            "mission_completion_rate": _clamp01(float(mission_completion_rate_value)),
            "protective_index": protective_index,
        },
    }
    explanations_fr = {
        "intensity": "Mesure si le temps d'écran quotidien dépasse les repères cliniques de l'âge.",
        "compulsivity": "Capte la fréquence d'ouverture, les sessions très courtes et les déblocages répétés.",
        "nocturnal": "Quantifie l'usage nocturne, associé à un risque de perturbation du sommeil.",
        "escalation": "Détecte une hausse rapide de l'usage d'une semaine à l'autre.",
        "imbalance": "Reflète un déséquilibre entre exposition écran et signaux protecteurs éducatifs/familiaux.",
    }
    return ScoringBundle(
        global_score=weighted_global(subscores, ADDICTION_WEIGHTS),
        subscores=subscores,
        feature_values=feature_values,
        explanations_fr=explanations_fr,
    )
