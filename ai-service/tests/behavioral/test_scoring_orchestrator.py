from __future__ import annotations

import random
from datetime import datetime

import pytest

from app.contracts.behavioral import BehavioralAnalysisRequest
from app.services.behavioral.scoring_orchestrator import score_behavioral_request


def _event(
    *,
    event_type: str,
    started_at: datetime,
    ended_at: datetime | None = None,
    duration_sec: int | None = None,
) -> dict:
    return {
        "eventType": event_type,
        "startedAt": started_at.isoformat(),
        "endedAt": ended_at.isoformat() if ended_at else None,
        "durationSec": duration_sec,
    }


def _build_profile_event(
    *,
    day: int,
    start_hour: int,
    start_minute: int,
    end_day_offset: int,
    end_hour: int,
    end_minute: int,
    duration_sec: int,
) -> dict:
    start = datetime(2026, 4, day, start_hour, start_minute)
    end = datetime(2026, 4, day + end_day_offset, end_hour, end_minute)
    return {
        "eventType": "app_session",
        "startedAt": start.isoformat(),
        "endedAt": end.isoformat(),
        "durationSec": duration_sec,
    }


def test_orchestrator_returns_contract_shape():
    req = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 12,
            "ageYears": 11,
            "windowDays": 7,
            "events": [
                _event(
                    event_type="app_session",
                    started_at=datetime(2026, 4, 20, 10, 0),
                    ended_at=datetime(2026, 4, 20, 11, 0),
                    duration_sec=3600,
                ),
                _event(
                    event_type="unlock",
                    started_at=datetime(2026, 4, 20, 8, 0),
                ),
            ],
            "contentAnalysesSummary": {
                "educationalCount": 7,
                "riskyCount": 1,
                "dangerousCount": 0,
                "total": 8,
            },
            "missionSummary": {"completed": 4, "assigned": 5, "successRate": 0.8},
        }
    )
    response = score_behavioral_request(req, computed_at=datetime(2026, 4, 21, 12, 0))

    assert 0.0 <= response.addiction_score <= 1.0
    assert 0.0 <= response.wellbeing_score <= 1.0
    assert response.window_days == 7
    assert len(response.addiction_subscores) == 5
    assert len(response.wellbeing_subscores) == 5
    assert {s.name for s in response.addiction_subscores} == {
        "intensity",
        "compulsivity",
        "nocturnal",
        "escalation",
        "imbalance",
    }
    assert {s.name for s in response.wellbeing_subscores} == {
        "screen_balance",
        "content_quality",
        "real_activity",
        "sleep",
        "family_interaction",
    }


def test_orchestrator_averages_daily_features_over_window_days():
    req = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 1,
            "ageYears": 12,
            "windowDays": 2,
            "events": [
                # Day A: 60 min session
                _event(
                    event_type="app_session",
                    started_at=datetime(2026, 4, 20, 10, 0),
                    ended_at=datetime(2026, 4, 20, 11, 0),
                    duration_sec=3600,
                ),
                # Day B: 120 min session
                _event(
                    event_type="app_session",
                    started_at=datetime(2026, 4, 21, 10, 0),
                    ended_at=datetime(2026, 4, 21, 12, 0),
                    duration_sec=7200,
                ),
            ],
        }
    )
    response = score_behavioral_request(req, computed_at=datetime(2026, 4, 21, 12, 0))
    intensity = next(s for s in response.addiction_subscores if s.name == "intensity")
    assert intensity.feature_values["avg_daily_screen_minutes"] == pytest.approx(90.0)


def test_orchestrator_handles_empty_events():
    req = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 5,
            "ageYears": 9,
            "windowDays": 7,
            "events": [],
        }
    )
    response = score_behavioral_request(req, computed_at=datetime(2026, 4, 21, 8, 0))
    assert response.addiction_score >= 0.0
    assert response.wellbeing_score >= 0.0
    assert next(s for s in response.addiction_subscores if s.name == "escalation").value == 0.0


def test_orchestrator_uses_summary_signals_as_is():
    low_quality = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 7,
            "ageYears": 13,
            "windowDays": 7,
            "events": [],
            "contentAnalysesSummary": {"educationalCount": 1, "riskyCount": 4, "dangerousCount": 5, "total": 10},
            "missionSummary": {"completed": 1, "assigned": 6},
        }
    )
    high_quality = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 7,
            "ageYears": 13,
            "windowDays": 7,
            "events": [],
            "contentAnalysesSummary": {"educationalCount": 9, "riskyCount": 1, "dangerousCount": 0, "total": 10},
            "missionSummary": {"completed": 6, "assigned": 6},
        }
    )
    low = score_behavioral_request(low_quality, computed_at=datetime(2026, 4, 21, 8, 0))
    high = score_behavioral_request(high_quality, computed_at=datetime(2026, 4, 21, 8, 0))

    low_content = next(s for s in low.wellbeing_subscores if s.name == "content_quality").value
    high_content = next(s for s in high.wellbeing_subscores if s.name == "content_quality").value
    low_family = next(s for s in low.wellbeing_subscores if s.name == "family_interaction").value
    high_family = next(s for s in high.wellbeing_subscores if s.name == "family_interaction").value
    assert high_content > low_content
    assert high_family > low_family


def test_no_stigmatizing_vocabulary_in_explanations():
    req = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 1,
            "ageYears": 11,
            "windowDays": 7,
            "events": [],
            "contentAnalysesSummary": {"educationalCount": 5, "riskyCount": 3, "dangerousCount": 2, "total": 10},
            "missionSummary": {"completed": 4, "assigned": 5},
        }
    )
    resp = score_behavioral_request(req, computed_at=datetime(2026, 4, 21, 12, 0))
    banned = {"addiction", "addictif", "accro", "dépendance"}
    all_exp = [s.explanation_fr for s in resp.addiction_subscores + resp.wellbeing_subscores]
    for exp in all_exp:
        low = exp.lower()
        for word in banned:
            assert word not in low, f"mot banni '{word}' trouvé dans : {exp}"


def test_balanced_child_9yo_profile():
    # 14-day event history avoids weekly slope insufficient-history bias; this profile
    # isolates intensity/nocturnal behavior without artificial escalation inflation.
    req = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 1,
            "ageYears": 9,
            "windowDays": 7,
            "events": [
                _build_profile_event(
                    day=7 + d,
                    start_hour=10,
                    start_minute=0,
                    end_day_offset=0,
                    end_hour=11,
                    end_minute=30,
                    duration_sec=5400,
                )
                for d in range(14)
            ],
            "contentAnalysesSummary": {"educationalCount": 30, "riskyCount": 15, "dangerousCount": 5, "total": 50},
            "missionSummary": {"completed": 8, "assigned": 10, "successRate": 0.8},
        }
    )
    resp = score_behavioral_request(req, computed_at=datetime(2026, 4, 21, 12, 0))
    assert 0.05 <= resp.addiction_score <= 0.25, f"addiction={resp.addiction_score}"
    assert 0.55 <= resp.wellbeing_score <= 0.90, f"wellbeing={resp.wellbeing_score}"


def test_intensive_nocturnal_teen_13yo_profile():
    # 14-day event history avoids weekly slope insufficient-history bias; this profile
    # keeps escalation neutral so intensity/nocturnal effects dominate.
    day_sessions = [
        _build_profile_event(
            day=7 + d,
            start_hour=18,
            start_minute=0,
            end_day_offset=0,
            end_hour=21,
            end_minute=30,
            duration_sec=12600,
        )
        for d in range(14)
    ]
    nocturnal_sessions = [
        _build_profile_event(
            day=7 + d,
            start_hour=23,
            start_minute=0,
            end_day_offset=1,
            end_hour=0,
            end_minute=30,
            duration_sec=5400,
        )
        for d in range(14)
    ]
    req = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 2,
            "ageYears": 13,
            "windowDays": 7,
            "events": [*day_sessions, *nocturnal_sessions],
            "contentAnalysesSummary": {"educationalCount": 2, "riskyCount": 20, "dangerousCount": 28, "total": 50},
            "missionSummary": {"completed": 2, "assigned": 10, "successRate": 0.2},
        }
    )
    resp = score_behavioral_request(req, computed_at=datetime(2026, 4, 21, 12, 0))
    assert 0.40 <= resp.addiction_score <= 0.70, f"addiction={resp.addiction_score}"
    assert 0.05 <= resp.wellbeing_score <= 0.35, f"wellbeing={resp.wellbeing_score}"


def test_global_coherence_random_profiles():
    rng = random.Random(42)
    addiction_names = {"intensity", "compulsivity", "nocturnal", "escalation", "imbalance"}
    wellbeing_names = {"screen_balance", "content_quality", "real_activity", "sleep", "family_interaction"}
    for i in range(20):
        events = []
        for _ in range(rng.randint(0, 30)):
            start = datetime(2026, 4, 14 + rng.randint(0, 6), rng.randint(0, 23), 0)
            duration = rng.randint(60, 7200)
            events.append(
                {
                    "eventType": "app_session",
                    "startedAt": start.isoformat(),
                    "durationSec": duration,
                }
            )
        req = BehavioralAnalysisRequest.model_validate(
            {
                "userId": i,
                "ageYears": rng.randint(5, 17),
                "windowDays": 7,
                "events": events,
                "contentAnalysesSummary": {
                    "educationalCount": rng.randint(0, 50),
                    "riskyCount": rng.randint(0, 30),
                    "dangerousCount": rng.randint(0, 20),
                    "total": rng.randint(0, 100),
                },
                "missionSummary": {
                    "completed": rng.randint(0, 10),
                    "assigned": rng.randint(0, 10),
                },
            }
        )
        resp = score_behavioral_request(req, computed_at=datetime(2026, 4, 21, 12, 0))
        assert 0.0 <= resp.addiction_score <= 1.0
        assert 0.0 <= resp.wellbeing_score <= 1.0
        assert len(resp.addiction_subscores) == 5
        assert len(resp.wellbeing_subscores) == 5
        assert {s.name for s in resp.addiction_subscores} == addiction_names
        assert {s.name for s in resp.wellbeing_subscores} == wellbeing_names
