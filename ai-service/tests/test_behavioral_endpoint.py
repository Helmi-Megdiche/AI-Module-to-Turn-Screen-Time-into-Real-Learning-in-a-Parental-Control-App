from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


def _balanced_payload() -> dict:
    base = datetime(2026, 4, 7, 10, 0)
    events = []
    for d in range(14):
        start = base + timedelta(days=d)
        end = start + timedelta(minutes=90)
        events.append(
            {
                "eventType": "app_session",
                "startedAt": start.isoformat(),
                "endedAt": end.isoformat(),
                "durationSec": 5400,
            }
        )
    return {
        "userId": 1,
        "ageYears": 9,
        "windowDays": 7,
        "events": events,
        "contentAnalysesSummary": {
            "educationalCount": 30,
            "riskyCount": 15,
            "dangerousCount": 5,
            "total": 50,
        },
        "missionSummary": {
            "completed": 8,
            "assigned": 10,
            "successRate": 0.8,
        },
    }


def _risk_payload() -> dict:
    events = []
    for d in range(14):
        day_start = datetime(2026, 4, 7 + d, 18, 0)
        day_end = day_start + timedelta(minutes=210)
        night_start = datetime(2026, 4, 7 + d, 23, 0)
        night_end = night_start + timedelta(minutes=90)
        events.extend(
            [
                {
                    "eventType": "app_session",
                    "startedAt": day_start.isoformat(),
                    "endedAt": day_end.isoformat(),
                    "durationSec": 12600,
                },
                {
                    "eventType": "app_session",
                    "startedAt": night_start.isoformat(),
                    "endedAt": night_end.isoformat(),
                    "durationSec": 5400,
                },
            ]
        )
    return {
        "userId": 2,
        "ageYears": 13,
        "windowDays": 7,
        "events": events,
        "contentAnalysesSummary": {
            "educationalCount": 2,
            "riskyCount": 20,
            "dangerousCount": 28,
            "total": 50,
        },
        "missionSummary": {
            "completed": 2,
            "assigned": 10,
            "successRate": 0.2,
        },
    }


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main_module.ocr_service, "get_reader", lambda: object())
    monkeypatch.setattr(main_module, "initialize_moderation", lambda: True)
    monkeypatch.setattr(main_module.vision_service, "get_classifier", lambda: object())
    with TestClient(app) as c:
        yield c


def test_behavioral_analyze_happy_path(client: TestClient) -> None:
    response = client.post("/behavioral/analyze", json=_balanced_payload())
    assert response.status_code == 200
    body = response.json()
    assert "addictionScore" in body
    assert "wellbeingScore" in body
    assert "addictionSubscores" in body and len(body["addictionSubscores"]) == 5
    assert "wellbeingSubscores" in body and len(body["wellbeingSubscores"]) == 5
    assert "recommendations" in body
    assert "windowDays" in body
    assert "computedAt" in body


def test_behavioral_analyze_empty_events(client: TestClient) -> None:
    payload = _balanced_payload()
    payload["events"] = []
    response = client.post("/behavioral/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert 0.0 <= body["addictionScore"] <= 1.0
    assert 0.0 <= body["wellbeingScore"] <= 1.0


def test_behavioral_analyze_missing_required_field(client: TestClient) -> None:
    payload = _balanced_payload()
    payload.pop("userId")
    response = client.post("/behavioral/analyze", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_behavioral_analyze_invalid_age(client: TestClient) -> None:
    """
    Current behavior: negative age is accepted by the scoring pipeline and
    interpreted by threshold fallback logic; endpoint returns 200.
    """
    payload = _balanced_payload()
    payload["ageYears"] = -5
    response = client.post("/behavioral/analyze", json=payload)
    assert response.status_code == 200


def test_behavioral_analyze_recommendations_populated_for_risk_profile(client: TestClient) -> None:
    response = client.post("/behavioral/analyze", json=_risk_payload())
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    assert any(rec.get("severity") == "high" for rec in recs)


def test_behavioral_analyze_returns_camelcase_keys(client: TestClient) -> None:
    response = client.post("/behavioral/analyze", json=_risk_payload())
    assert response.status_code == 200
    body = response.json()
    assert "addictionScore" in body
    assert "wellbeingScore" in body
    assert "windowDays" in body
    assert "computedAt" in body
    assert all("featureValues" in s and "explanationFr" in s for s in body["addictionSubscores"])
    if body["recommendations"]:
        assert "messageFr" in body["recommendations"][0]
