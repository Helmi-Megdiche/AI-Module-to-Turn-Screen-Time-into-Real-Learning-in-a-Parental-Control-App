from __future__ import annotations

from datetime import datetime, timedelta

from app.contracts.behavioral import BehavioralAnalysisRequest, BehavioralAnalysisResponse
from app.services.behavioral.mission_engine import generate_missions
from app.services.behavioral.scoring_orchestrator import score_behavioral_request


ADDICTION_NAMES = ["intensity", "compulsivity", "nocturnal", "escalation", "imbalance"]
WELLBEING_NAMES = [
    "screen_balance",
    "content_quality",
    "real_activity",
    "sleep",
    "family_interaction",
]


def _response_with(
    addiction_overrides: dict[str, float] | None = None,
    wellbeing_overrides: dict[str, float] | None = None,
) -> BehavioralAnalysisResponse:
    addiction_values = {name: 0.2 for name in ADDICTION_NAMES}
    wellbeing_values = {name: 0.8 for name in WELLBEING_NAMES}
    addiction_values.update(addiction_overrides or {})
    wellbeing_values.update(wellbeing_overrides or {})

    return BehavioralAnalysisResponse.model_validate(
        {
            "addictionScore": 0.2,
            "addictionSubscores": [
                {
                    "name": name,
                    "value": addiction_values[name],
                    "featureValues": {},
                    "explanationFr": "ok",
                }
                for name in ADDICTION_NAMES
            ],
            "wellbeingScore": 0.8,
            "wellbeingSubscores": [
                {
                    "name": name,
                    "value": wellbeing_values[name],
                    "featureValues": {},
                    "explanationFr": "ok",
                }
                for name in WELLBEING_NAMES
            ],
            "windowDays": 14,
            "computedAt": datetime(2026, 4, 27, 12, 0),
            "recommendations": [],
            "missions": [],
        }
    )


def test_balanced_profile_returns_no_missions() -> None:
    response = _response_with()
    assert generate_missions(response, age_years=10) == []


def test_severe_nocturnal_returns_hard_mission() -> None:
    response = _response_with(addiction_overrides={"nocturnal": 0.95})
    missions = generate_missions(response, age_years=14)
    assert missions
    assert missions[0].difficulty == "hard"
    assert missions[0].points == 30
    assert missions[0].triggering_subscore == "nocturnal"
    assert missions[0].triggering_value == 0.95


def test_low_real_activity_returns_mission() -> None:
    response = _response_with(wellbeing_overrides={"real_activity": 0.1})
    missions = generate_missions(response, age_years=12)
    assert missions
    assert missions[0].triggering_subscore == "real_activity"
    assert missions[0].difficulty == "hard"


def test_max_two_missions_returned() -> None:
    response = _response_with(
        addiction_overrides={"nocturnal": 0.9, "intensity": 0.85, "escalation": 0.8},
        wellbeing_overrides={"family_interaction": 0.1},
    )
    missions = generate_missions(response, age_years=15)
    assert len(missions) == 2


def test_diversification_no_duplicate_subscore() -> None:
    response = _response_with(addiction_overrides={"nocturnal": 0.95})
    missions = generate_missions(response, age_years=15)
    assert len([m for m in missions if m.triggering_subscore == "nocturnal"]) == 1


def test_age_filtering_excludes_out_of_range() -> None:
    response = _response_with(addiction_overrides={"nocturnal": 0.99})
    missions = generate_missions(response, age_years=8)
    descriptions = [m.description_fr for m in missions]
    assert "Mets ton téléphone en mode avion une heure avant de dormir cette semaine." not in descriptions


def test_difficulty_scaling() -> None:
    easy = generate_missions(_response_with(addiction_overrides={"intensity": 0.55}), age_years=10)
    medium = generate_missions(_response_with(addiction_overrides={"intensity": 0.7}), age_years=10)
    hard = generate_missions(_response_with(addiction_overrides={"intensity": 0.9}), age_years=10)
    assert easy[0].difficulty == "easy"
    assert medium[0].difficulty == "medium"
    assert hard[0].difficulty == "hard"


def test_french_no_stigmatizing_vocabulary() -> None:
    response = _response_with(
        addiction_overrides={
            "nocturnal": 0.95,
            "intensity": 0.95,
            "compulsivity": 0.95,
            "escalation": 0.95,
            "imbalance": 0.95,
        },
        wellbeing_overrides={
            "real_activity": 0.05,
            "family_interaction": 0.05,
            "sleep": 0.05,
            "content_quality": 0.05,
            "screen_balance": 0.05,
        },
    )
    missions = generate_missions(response, age_years=14)
    text = " ".join(m.description_fr.lower() for m in missions)
    for bad in ("addict", "accro", "dépendance", "drogue"):
        assert bad not in text


def test_french_accents_preserved() -> None:
    response = _response_with(addiction_overrides={"nocturnal": 0.95})
    missions = generate_missions(response, age_years=14)
    text = " ".join(m.description_fr for m in missions)
    assert any(ch in text for ch in ("é", "è", "à"))


def test_triggering_value_is_raw_not_severity() -> None:
    response = _response_with(wellbeing_overrides={"real_activity": 0.15})
    missions = generate_missions(response, age_years=13)
    target = next(m for m in missions if m.triggering_subscore == "real_activity")
    assert target.triggering_value == 0.15


def test_orchestrator_attaches_missions() -> None:
    start = datetime(2026, 4, 20, 23, 0)
    events = []
    for i in range(7):
        started = start + timedelta(days=i)
        events.append(
            {
                "eventType": "app_session",
                "startedAt": started.isoformat(),
                "durationSec": 7200,
                "packageName": "com.video.app",
            }
        )
    request = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 9001,
            "ageYears": 11,
            "windowDays": 7,
            "events": events,
            "contentAnalysesSummary": {
                "educationalCount": 2,
                "riskyCount": 3,
                "dangerousCount": 0,
                "total": 15,
            },
            "missionSummary": {"completed": 1, "assigned": 10},
        }
    )
    response = score_behavioral_request(request, computed_at=datetime(2026, 4, 27, 12, 0))
    assert response.missions
