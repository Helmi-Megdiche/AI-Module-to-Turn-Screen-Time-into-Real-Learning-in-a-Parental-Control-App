from __future__ import annotations

from dataclasses import dataclass

from app.services.behavioral.scoring_utils import inverse_score, saturating_score, weighted_global
from app.services.behavioral.thresholds import (
    NOCTURNAL_CRITICAL_MINUTES,
    WELLBEING_WEIGHTS,
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


def score_wellbeing(
    *,
    age_years: int,
    avg_daily_screen_minutes: float,
    avg_daily_nocturnal_minutes: float,
    content_quality_ratio_value: float,
    mission_completion_rate_value: float,
    mission_assigned_count: int,
) -> ScoringBundle:
    """
    Compute wellbeing score + five explainable subscores.

    family_interaction subscore:
    proxy via mission_summary ; seam pour événements dashboard parent en future work.
    """
    age_threshold_min = float(get_age_screen_threshold(age_years))

    screen_balance = inverse_score(saturating_score(avg_daily_screen_minutes, age_threshold_min))

    content_quality = _clamp01(float(content_quality_ratio_value))

    real_activity = _clamp01(float(mission_completion_rate_value))

    sleep = inverse_score(saturating_score(avg_daily_nocturnal_minutes, float(NOCTURNAL_CRITICAL_MINUTES)))

    mission_rate = _clamp01(float(mission_completion_rate_value))
    assignment_presence = min(1.0, max(0.0, float(mission_assigned_count)) / 5.0)
    family_interaction = _clamp01(0.7 * mission_rate + 0.3 * assignment_presence)

    subscores = {
        "screen_balance": _clamp01(screen_balance),
        "content_quality": content_quality,
        "real_activity": _clamp01(real_activity),
        "sleep": _clamp01(sleep),
        "family_interaction": family_interaction,
    }
    feature_values = {
        "screen_balance": {
            "avg_daily_screen_minutes": float(avg_daily_screen_minutes),
            "age_threshold_minutes": age_threshold_min,
        },
        "content_quality": {
            "content_quality_ratio": content_quality,
        },
        "real_activity": {
            "mission_completion_rate": _clamp01(float(mission_completion_rate_value)),
        },
        "sleep": {
            "avg_daily_nocturnal_minutes": float(avg_daily_nocturnal_minutes),
            "critical_nocturnal_minutes": float(NOCTURNAL_CRITICAL_MINUTES),
        },
        "family_interaction": {
            "mission_completion_rate": mission_rate,
            "mission_assigned_count": float(max(0, mission_assigned_count)),
            "assignment_presence": assignment_presence,
            "formula": 0.7 * mission_rate + 0.3 * assignment_presence,
        },
    }
    explanations_fr = {
        "screen_balance": "Mesure l'équilibre du temps d'écran par rapport aux repères de l'âge.",
        "content_quality": "Valorise la proportion de contenus éducatifs parmi les usages analysés.",
        "real_activity": "Valorise la proportion de missions hors écran réellement accomplies.",
        "sleep": "Pénalise l'usage nocturne susceptible d'impacter la qualité du sommeil.",
        "family_interaction": "Proxy via mission_summary ; évolution prévue avec les événements dashboard parent.",
    }
    return ScoringBundle(
        global_score=weighted_global(subscores, WELLBEING_WEIGHTS),
        subscores=subscores,
        feature_values=feature_values,
        explanations_fr=explanations_fr,
    )
