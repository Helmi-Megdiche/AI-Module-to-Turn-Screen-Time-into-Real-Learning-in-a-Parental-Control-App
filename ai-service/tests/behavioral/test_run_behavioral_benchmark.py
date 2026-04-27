"""Unit tests for behavioral benchmark runner."""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.behavioral.scripts.run_behavioral_benchmark import (
    execute_benchmark,
    load_profiles,
    main,
)


def _profiles_path() -> Path:
    return Path("evaluation/behavioral/datasets/behavioral_profiles_v1.json").resolve()


def test_runner_loads_profiles_json() -> None:
    profiles = load_profiles(_profiles_path())
    assert isinstance(profiles, list)
    assert len(profiles) == 15


def test_runner_runs_all_profiles_end_to_end(tmp_path: Path) -> None:
    report_path = tmp_path / "first_run_actuals.md"
    export_path = tmp_path / "first_run_actuals.json"
    payload = execute_benchmark(
        profiles_path=_profiles_path(),
        report_path=report_path,
        export_actuals_path=export_path,
    )
    assert payload["profile_count"] == 15
    assert report_path.is_file()
    assert export_path.is_file()


def test_runner_generates_markdown_with_expected_sections(tmp_path: Path) -> None:
    report_path = tmp_path / "first_run_actuals.md"
    execute_benchmark(
        profiles_path=_profiles_path(),
        report_path=report_path,
        export_actuals_path=None,
    )
    content = report_path.read_text(encoding="utf-8")
    assert "# Behavioral Benchmark Report (actuals)" in content
    assert "## Run metadata" in content
    assert "## Recommendation rule coverage" in content
    assert "## Profile summary table" in content
    assert "| Missions |" in content


def test_runner_assert_ranges_includes_range_ok_in_profiles(tmp_path: Path) -> None:
    profiles = load_profiles(_profiles_path())
    for profile in profiles:
        profile["expected_addiction_range"] = [0.0, 1.0]
        profile["expected_wellbeing_range"] = [0.0, 1.0]
    custom_profiles = tmp_path / "profiles_with_ranges.json"
    custom_profiles.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = tmp_path / "baseline.md"
    payload = execute_benchmark(
        profiles_path=custom_profiles,
        report_path=report_path,
        export_actuals_path=None,
        assert_ranges=True,
    )
    assert all(row["range_ok"] is True for row in payload["profiles"])
    assert all("missions_ok" in row for row in payload["profiles"])
    assert "Score range pass rate" in report_path.read_text(encoding="utf-8")


def test_runner_assert_ranges_can_mark_profiles_out_of_range(tmp_path: Path) -> None:
    profiles = load_profiles(_profiles_path())
    for profile in profiles:
        profile["expected_addiction_range"] = [0.0, 0.01]
        profile["expected_wellbeing_range"] = [0.0, 0.01]
    custom_profiles = tmp_path / "profiles_tight_ranges.json"
    custom_profiles.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = execute_benchmark(
        profiles_path=custom_profiles,
        report_path=tmp_path / "tight.md",
        export_actuals_path=None,
        assert_ranges=True,
    )
    assert any(row["range_ok"] is False for row in payload["profiles"])


def test_runner_main_returns_zero_even_when_expectation_checks_fail(tmp_path: Path) -> None:
    failing_profile = [
        {
            "id": "failing_case",
            "age_years": 9,
            "seed": 1,
            "description_fr": "profile intentionally forcing expectation mismatch",
            "generator": {
                "window_days": 14,
                "base_daily_minutes": 0,
                "daily_minutes_growth_per_day": 0.0,
                "sessions_per_day": 0,
                "short_session_fraction": 0.0,
                "unlocks_per_day": 0,
                "nocturnal_minutes_per_day": 0,
                "active_hours": [10, 19],
                "weekend_multiplier": 1.0,
            },
            "content_analyses_summary": {"educational_count": 0, "risky_count": 0, "dangerous_count": 0, "total": 0},
            "mission_summary": {"completed": 0, "assigned": 0},
            "required_recommendations": ["screen_curfew"],
            "forbidden_recommendations": [],
        }
    ]
    profiles_path = tmp_path / "failing_profiles.json"
    profiles_path.write_text(json.dumps(failing_profile, ensure_ascii=False), encoding="utf-8")
    export_path = tmp_path / "actuals.json"

    code = main(
        [
            "--profiles",
            str(profiles_path),
            "--report-name",
            "phase6a_test.md",
            "--export-actuals",
            str(export_path),
        ]
    )

    assert code == 0
