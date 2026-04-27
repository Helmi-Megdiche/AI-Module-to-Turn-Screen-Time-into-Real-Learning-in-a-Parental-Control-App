"""Unit tests for profile-range calibration script."""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.behavioral.scripts.calibrate_profiles import calibrate_profiles


def _profiles_fixture() -> list[dict]:
    return [
        {
            "id": "p1",
            "age_years": 9,
            "seed": 1,
            "description_fr": "a",
            "generator": {"window_days": 14},
            "content_analyses_summary": {"educational_count": 1, "risky_count": 0, "dangerous_count": 0, "total": 1},
            "mission_summary": {"completed": 1, "assigned": 1},
            "required_recommendations": [],
            "forbidden_recommendations": [],
        },
        {
            "id": "p2",
            "age_years": 10,
            "seed": 2,
            "description_fr": "b",
            "generator": {"window_days": 14},
            "content_analyses_summary": {"educational_count": 0, "risky_count": 1, "dangerous_count": 0, "total": 1},
            "mission_summary": {"completed": 0, "assigned": 1},
            "required_recommendations": [],
            "forbidden_recommendations": [],
        },
    ]


def _actuals_fixture() -> dict:
    return {
        "profiles": [
            {"id": "p1", "addiction_score": 0.5, "wellbeing_score": 0.8},
            {"id": "p2", "addiction_score": 0.02, "wellbeing_score": 0.97},
        ]
    }


def test_calibrate_profiles_applies_expected_ranges_with_tolerance(tmp_path: Path) -> None:
    profiles_path = tmp_path / "profiles.json"
    actuals_path = tmp_path / "actuals.json"
    profiles_path.write_text(json.dumps(_profiles_fixture(), ensure_ascii=False, indent=2), encoding="utf-8")
    actuals_path.write_text(json.dumps(_actuals_fixture(), ensure_ascii=False, indent=2), encoding="utf-8")

    changes = calibrate_profiles(profiles_path=profiles_path, actuals_path=actuals_path, tolerance=0.08)
    calibrated = json.loads(profiles_path.read_text(encoding="utf-8"))
    assert len(changes) == 2
    assert calibrated[0]["expected_addiction_range"] == [0.42, 0.58]
    assert calibrated[0]["expected_wellbeing_range"] == [0.72, 0.88]


def test_calibrate_profiles_clamps_ranges_to_zero_one(tmp_path: Path) -> None:
    profiles_path = tmp_path / "profiles.json"
    actuals_path = tmp_path / "actuals.json"
    profiles_path.write_text(json.dumps(_profiles_fixture(), ensure_ascii=False, indent=2), encoding="utf-8")
    actuals_path.write_text(json.dumps(_actuals_fixture(), ensure_ascii=False, indent=2), encoding="utf-8")

    calibrate_profiles(profiles_path=profiles_path, actuals_path=actuals_path, tolerance=0.1)
    calibrated = json.loads(profiles_path.read_text(encoding="utf-8"))
    assert calibrated[1]["expected_addiction_range"] == [0.0, 0.12]
    assert calibrated[1]["expected_wellbeing_range"] == [0.87, 1.0]


def test_calibrate_profiles_preserves_non_range_fields(tmp_path: Path) -> None:
    profiles = _profiles_fixture()
    profiles_path = tmp_path / "profiles.json"
    actuals_path = tmp_path / "actuals.json"
    profiles_path.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")
    actuals_path.write_text(json.dumps(_actuals_fixture(), ensure_ascii=False, indent=2), encoding="utf-8")

    calibrate_profiles(profiles_path=profiles_path, actuals_path=actuals_path, tolerance=0.08)
    calibrated = json.loads(profiles_path.read_text(encoding="utf-8"))
    assert calibrated[0]["id"] == profiles[0]["id"]
    assert calibrated[0]["seed"] == profiles[0]["seed"]
    assert calibrated[1]["description_fr"] == profiles[1]["description_fr"]


def test_calibrate_profiles_is_idempotent(tmp_path: Path) -> None:
    profiles_path = tmp_path / "profiles.json"
    actuals_path = tmp_path / "actuals.json"
    profiles_path.write_text(json.dumps(_profiles_fixture(), ensure_ascii=False, indent=2), encoding="utf-8")
    actuals_path.write_text(json.dumps(_actuals_fixture(), ensure_ascii=False, indent=2), encoding="utf-8")

    calibrate_profiles(profiles_path=profiles_path, actuals_path=actuals_path, tolerance=0.08)
    first = profiles_path.read_text(encoding="utf-8")
    calibrate_profiles(profiles_path=profiles_path, actuals_path=actuals_path, tolerance=0.08)
    second = profiles_path.read_text(encoding="utf-8")
    assert first == second
