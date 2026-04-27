"""Unit tests for ``app.contracts.behavioral`` (Pydantic v2 models)."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.contracts.behavioral import (
    BehavioralAnalysisRequest,
    BehavioralAnalysisResponse,
    ContentAnalysesSummary,
    MissionSummary,
    SubScore,
    UsageEventPayload,
)


# === UsageEventPayload ===


def test_usage_event_accepts_camel_case_wire_format():
    payload = UsageEventPayload.model_validate(
        {
            "eventType": "app_session",
            "appPackage": "com.example",
            "startedAt": "2026-04-20T10:00:00",
            "endedAt": "2026-04-20T10:05:00",
            "durationSec": 300,
        }
    )
    assert payload.event_type == "app_session"
    assert payload.app_package == "com.example"
    assert payload.started_at == datetime(2026, 4, 20, 10, 0, 0)
    assert payload.ended_at == datetime(2026, 4, 20, 10, 5, 0)
    assert payload.duration_sec == 300


def test_usage_event_accepts_snake_case_python_format():
    payload = UsageEventPayload.model_validate(
        {
            "event_type": "unlock",
            "app_package": None,
            "started_at": datetime(2026, 4, 20, 8, 0, 0),
        }
    )
    assert payload.event_type == "unlock"
    assert payload.ended_at is None
    assert payload.duration_sec is None


def test_usage_event_rejects_invalid_event_type():
    with pytest.raises(ValidationError):
        UsageEventPayload.model_validate(
            {"eventType": "not_a_real_type", "startedAt": "2026-04-20T10:00:00"}
        )


def test_usage_event_extra_fields_ignored():
    payload = UsageEventPayload.model_validate(
        {
            "eventType": "screen_on",
            "startedAt": "2026-04-20T10:00:00",
            "unknownField": "ignored",
        }
    )
    assert payload.event_type == "screen_on"
    assert not hasattr(payload, "unknownField")


def test_usage_event_requires_started_at():
    with pytest.raises(ValidationError):
        UsageEventPayload.model_validate({"eventType": "unlock"})


def test_usage_event_serializes_with_camel_case_aliases():
    payload = UsageEventPayload(
        event_type="app_session",
        app_package="com.x",
        started_at=datetime(2026, 4, 20, 10),
        ended_at=datetime(2026, 4, 20, 11),
        duration_sec=3600,
    )
    wire = payload.model_dump(by_alias=True)
    assert wire["eventType"] == "app_session"
    assert wire["startedAt"] == datetime(2026, 4, 20, 10)
    assert wire["durationSec"] == 3600


# === ContentAnalysesSummary ===


def test_content_summary_defaults_are_zero():
    summary = ContentAnalysesSummary()
    assert summary.educational_count == 0
    assert summary.risky_count == 0
    assert summary.dangerous_count == 0
    assert summary.total == 0


def test_content_summary_camel_case_input():
    summary = ContentAnalysesSummary.model_validate(
        {"educationalCount": 5, "riskyCount": 2, "dangerousCount": 1, "total": 8}
    )
    assert summary.educational_count == 5
    assert summary.risky_count == 2
    assert summary.dangerous_count == 1
    assert summary.total == 8


# === MissionSummary ===


def test_mission_summary_defaults_are_zero():
    summary = MissionSummary()
    assert summary.completed == 0
    assert summary.assigned == 0
    assert summary.success_rate == 0.0


def test_mission_summary_camel_case_input():
    summary = MissionSummary.model_validate(
        {"completed": 4, "assigned": 5, "successRate": 0.8}
    )
    assert summary.completed == 4
    assert summary.assigned == 5
    assert summary.success_rate == 0.8


# === BehavioralAnalysisRequest ===


def test_request_minimal_valid_payload():
    req = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 42,
            "ageYears": 10,
            "events": [
                {
                    "eventType": "app_session",
                    "startedAt": "2026-04-20T10:00:00",
                    "endedAt": "2026-04-20T10:30:00",
                    "durationSec": 1800,
                }
            ],
        }
    )
    assert req.user_id == 42
    assert req.age_years == 10
    assert req.window_days == 7  # default
    assert len(req.events) == 1
    assert req.content_analyses_summary is None
    assert req.mission_summary is None


def test_request_full_payload_with_summaries():
    req = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 1,
            "ageYears": 14,
            "windowDays": 14,
            "events": [],
            "contentAnalysesSummary": {
                "educationalCount": 2,
                "riskyCount": 1,
                "dangerousCount": 0,
                "total": 3,
            },
            "missionSummary": {"completed": 3, "assigned": 5, "successRate": 0.6},
        }
    )
    assert req.window_days == 14
    assert req.content_analyses_summary is not None
    assert req.content_analyses_summary.educational_count == 2
    assert req.mission_summary is not None
    assert req.mission_summary.completed == 3


def test_request_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        BehavioralAnalysisRequest.model_validate({"ageYears": 10, "events": []})


def test_request_accepts_snake_case_as_well():
    req = BehavioralAnalysisRequest.model_validate(
        {"user_id": 3, "age_years": 8, "events": []}
    )
    assert req.user_id == 3
    assert req.age_years == 8


# === SubScore / BehavioralAnalysisResponse ===


def test_subscore_round_trip():
    # Response-side models (SubScore / BehavioralAnalysisResponse) accept only
    # camelCase aliases by design: they model the exact wire format we emit.
    sub = SubScore.model_validate(
        {
            "name": "intensity",
            "value": 0.42,
            "featureValues": {"daily_minutes": 120.0},
            "explanationFr": "Temps d'écran élevé sur 7 jours.",
        }
    )
    wire = sub.model_dump(by_alias=True)
    assert wire["name"] == "intensity"
    assert wire["featureValues"] == {"daily_minutes": 120.0}
    assert wire["explanationFr"].startswith("Temps")


def test_response_full_shape():
    resp = BehavioralAnalysisResponse.model_validate(
        {
            "addictionScore": 0.6,
            "addictionSubscores": [
                {
                    "name": "intensity",
                    "value": 0.5,
                    "featureValues": {"x": 1.0},
                    "explanationFr": "Intense",
                }
            ],
            "wellbeingScore": 0.7,
            "wellbeingSubscores": [
                {
                    "name": "screen_balance",
                    "value": 0.8,
                    "featureValues": {"y": 2.0},
                    "explanationFr": "OK",
                }
            ],
            "windowDays": 7,
            "computedAt": datetime(2026, 4, 20, 12, 0, 0),
        }
    )
    wire = resp.model_dump(by_alias=True)
    assert wire["addictionScore"] == 0.6
    assert wire["wellbeingScore"] == 0.7
    assert wire["windowDays"] == 7
    assert wire["addictionSubscores"][0]["featureValues"] == {"x": 1.0}


def test_response_parses_from_camel_case_wire_format():
    resp = BehavioralAnalysisResponse.model_validate(
        {
            "addictionScore": 0.3,
            "addictionSubscores": [
                {
                    "name": "compulsivity",
                    "value": 0.2,
                    "featureValues": {"sessions": 25},
                    "explanationFr": "Peu compulsif",
                }
            ],
            "wellbeingScore": 0.9,
            "wellbeingSubscores": [],
            "windowDays": 7,
            "computedAt": "2026-04-20T12:00:00",
        }
    )
    assert resp.addiction_score == 0.3
    assert resp.addiction_subscores[0].feature_values == {"sessions": 25}
    assert resp.wellbeing_subscores == []
