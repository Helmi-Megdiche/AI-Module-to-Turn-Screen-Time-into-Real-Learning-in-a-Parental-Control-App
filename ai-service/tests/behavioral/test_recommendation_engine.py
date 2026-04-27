from __future__ import annotations

from datetime import datetime

import pytest

from app.contracts.behavioral import (
    BehavioralAnalysisRequest,
    BehavioralAnalysisResponse,
    RecommendationItem,
)
from app.services.behavioral.recommendation_engine import generate_recommendations
from app.services.behavioral.scoring_orchestrator import score_behavioral_request


def _response(
    *,
    addiction: dict[str, float] | None = None,
    wellbeing: dict[str, float] | None = None,
    wellbeing_score: float = 0.7,
) -> BehavioralAnalysisResponse:
    addiction_values = {
        "intensity": 0.2,
        "compulsivity": 0.2,
        "nocturnal": 0.2,
        "escalation": 0.1,
        "imbalance": 0.2,
    }
    if addiction:
        addiction_values.update(addiction)
    wellbeing_values = {
        "screen_balance": 0.8,
        "content_quality": 0.8,
        "real_activity": 0.8,
        "sleep": 0.8,
        "family_interaction": 0.8,
    }
    if wellbeing:
        wellbeing_values.update(wellbeing)
    return BehavioralAnalysisResponse.model_validate(
        {
            "addictionScore": 0.4,
            "addictionSubscores": [
                {
                    "name": name,
                    "value": value,
                    "featureValues": {},
                    "explanationFr": "exp",
                }
                for name, value in addiction_values.items()
            ],
            "wellbeingScore": wellbeing_score,
            "wellbeingSubscores": [
                {
                    "name": name,
                    "value": value,
                    "featureValues": {},
                    "explanationFr": "exp",
                }
                for name, value in wellbeing_values.items()
            ],
            "windowDays": 7,
            "computedAt": datetime(2026, 4, 21, 12, 0).isoformat(),
        }
    )


def _types(response: BehavioralAnalysisResponse) -> list[str]:
    return [r.type for r in generate_recommendations(response)]


@pytest.mark.parametrize(
    ("name", "response"),
    [
        ("screen_curfew", _response(addiction={"nocturnal": 0.7})),
        ("weekly_escalation_alert", _response(addiction={"escalation": 0.7})),
        ("daily_limit_reminder", _response(addiction={"intensity": 0.8})),
        ("session_break", _response(addiction={"compulsivity": 0.8})),
        ("imbalance_warning", _response(addiction={"imbalance": 0.8})),
        ("real_activity_prompt", _response(wellbeing={"real_activity": 0.2})),
        ("educational_boost", _response(addiction={"intensity": 0.4}, wellbeing={"content_quality": 0.2})),
        ("family_time_suggestion", _response(wellbeing={"family_interaction": 0.2})),
        ("balance_celebration", _response(wellbeing_score=0.8)),
    ],
)
def test_rule_positive_cases(name: str, response: BehavioralAnalysisResponse):
    recs = generate_recommendations(response)
    assert any(r.type == name for r in recs)


@pytest.mark.parametrize(
    ("name", "response"),
    [
        ("screen_curfew", _response(addiction={"nocturnal": 0.6})),
        ("weekly_escalation_alert", _response(addiction={"escalation": 0.5})),
        ("daily_limit_reminder", _response(addiction={"intensity": 0.45})),
        ("session_break", _response(addiction={"compulsivity": 0.35})),
        ("imbalance_warning", _response(addiction={"imbalance": 0.7})),
        ("real_activity_prompt", _response(wellbeing={"real_activity": 0.3})),
        ("educational_boost", _response(addiction={"intensity": 0.2}, wellbeing={"content_quality": 0.2})),
        ("family_time_suggestion", _response(wellbeing={"family_interaction": 0.3})),
        ("balance_celebration", _response(wellbeing_score=0.65)),
    ],
)
def test_rule_negative_cases(name: str, response: BehavioralAnalysisResponse):
    recs = generate_recommendations(response)
    assert not any(r.type == name for r in recs)


def test_ordering_and_celebration_blocked_when_high_exists():
    response = _response(
        addiction={
            "nocturnal": 0.7,  # high
            "compulsivity": 0.8,  # medium
            "intensity": 0.5,  # needed for educational_boost conjunction
        },
        wellbeing={"content_quality": 0.2},  # low
        wellbeing_score=0.8,
    )
    assert _types(response) == ["screen_curfew", "session_break", "educational_boost"]


def test_celebration_last_when_eligible():
    response = _response(wellbeing_score=0.8)
    recs = generate_recommendations(response)
    assert len(recs) == 1
    assert recs[-1].type == "balance_celebration"
    assert recs[-1].severity == "positive"


def test_empty_output_when_no_trigger_and_wellbeing_not_high_enough():
    response = _response(wellbeing_score=0.7)
    assert generate_recommendations(response) == []


@pytest.mark.parametrize(
    "response",
    [
        _response(addiction={"nocturnal": 0.7}),
        _response(addiction={"escalation": 0.7}),
        _response(addiction={"intensity": 0.8}),
        _response(addiction={"compulsivity": 0.8}),
        _response(addiction={"imbalance": 0.8}),
        _response(wellbeing={"real_activity": 0.2}),
        _response(addiction={"intensity": 0.4}, wellbeing={"content_quality": 0.2}),
        _response(wellbeing={"family_interaction": 0.2}),
        _response(wellbeing_score=0.8),
    ],
)
def test_no_stigmatizing_words_across_all_rule_messages(response: BehavioralAnalysisResponse):
    banned = {"addiction", "addictif", "accro", "dépendance"}
    recs = generate_recommendations(response)
    assert recs, "Expected at least one recommendation in this rule-trigger scenario."
    for rec in recs:
        low = rec.message_fr.lower()
        for word in banned:
            assert word not in low, f"mot banni '{word}' trouvé dans : {rec.message_fr}"


def test_contract_shape_of_generated_recommendations():
    response = _response(
        addiction={"nocturnal": 0.7, "imbalance": 0.8},
        wellbeing={"real_activity": 0.2, "content_quality": 0.2},
    )
    recs = generate_recommendations(response)
    assert recs
    for rec in recs:
        validated = RecommendationItem.model_validate(rec.model_dump(by_alias=True))
        assert validated.severity in {"low", "medium", "high", "positive"}
        assert validated.target_audience in {"parent", "child", "both"}


def test_integration_orchestrator_intensive_profile_has_expected_recommendations():
    day_sessions = [
        {
            "eventType": "app_session",
            "startedAt": datetime(2026, 4, 7 + d, 18, 0).isoformat(),
            "endedAt": datetime(2026, 4, 7 + d, 21, 30).isoformat(),
            "durationSec": 12600,
        }
        for d in range(14)
    ]
    nocturnal_sessions = [
        {
            "eventType": "app_session",
            "startedAt": datetime(2026, 4, 7 + d, 23, 0).isoformat(),
            "endedAt": datetime(2026, 4, 8 + d, 0, 30).isoformat(),
            "durationSec": 5400,
        }
        for d in range(14)
    ]
    req = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 2,
            "ageYears": 13,
            "windowDays": 7,
            "events": [*day_sessions, *nocturnal_sessions],
            "contentAnalysesSummary": {
                "educationalCount": 2,
                "riskyCount": 20,
                "dangerousCount": 28,
                "total": 50,
            },
            "missionSummary": {"completed": 2, "assigned": 10, "successRate": 0.2},
        }
    )
    resp = score_behavioral_request(req, computed_at=datetime(2026, 4, 21, 12, 0))
    assert len(resp.recommendations) >= 2
    assert any(r.type == "screen_curfew" for r in resp.recommendations)


def test_integration_orchestrator_balanced_profile_has_celebration():
    req = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 1,
            "ageYears": 9,
            "windowDays": 7,
            "events": [
                {
                    "eventType": "app_session",
                    "startedAt": datetime(2026, 4, 7 + d, 10, 0).isoformat(),
                    "endedAt": datetime(2026, 4, 7 + d, 11, 30).isoformat(),
                    "durationSec": 5400,
                }
                for d in range(14)
            ],
            "contentAnalysesSummary": {
                "educationalCount": 30,
                "riskyCount": 15,
                "dangerousCount": 5,
                "total": 50,
            },
            "missionSummary": {"completed": 8, "assigned": 10, "successRate": 0.8},
        }
    )
    resp = score_behavioral_request(req, computed_at=datetime(2026, 4, 21, 12, 0))
    assert any(r.type == "balance_celebration" for r in resp.recommendations)
