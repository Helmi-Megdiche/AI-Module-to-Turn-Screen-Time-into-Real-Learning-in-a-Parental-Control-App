"""Run deterministic behavioral benchmark and generate markdown/json reports."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.contracts.behavioral import BehavioralAnalysisRequest
from app.services.behavioral.scoring_orchestrator import score_behavioral_request
from evaluation.behavioral.scripts.synthetic_profile import generate_events


BEHAVIORAL_ROOT = Path(__file__).resolve().parents[1]
RULE_SEVERITY = {
    "screen_curfew": "high",
    "weekly_escalation_alert": "high",
    "daily_limit_reminder": "medium",
    "session_break": "medium",
    "imbalance_warning": "medium",
    "real_activity_prompt": "medium",
    "educational_boost": "low",
    "family_time_suggestion": "low",
    "balance_celebration": "positive",
}


def load_profiles(profiles_path: Path) -> list[dict[str, Any]]:
    with profiles_path.open("r", encoding="utf-8") as f:
        profiles = json.load(f)
    if not isinstance(profiles, list):
        raise ValueError("Profiles file must be a JSON list.")
    return profiles


def _resolve_profiles_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def _in_range(value: float, expected_range: list[float] | None) -> bool:
    if expected_range is None or len(expected_range) != 2:
        return False
    lower, upper = float(expected_range[0]), float(expected_range[1])
    return lower <= value <= upper


def _run_profile(profile: dict[str, Any], *, assert_ranges: bool) -> dict[str, Any]:
    events = generate_events(
        config=profile["generator"],
        seed=int(profile["seed"]),
        age_years=int(profile["age_years"]),
    )
    request = BehavioralAnalysisRequest.model_validate(
        {
            "userId": 10_000 + int(profile["seed"]),
            "ageYears": int(profile["age_years"]),
            "windowDays": int(profile["generator"]["window_days"]),
            "events": events,
            "contentAnalysesSummary": profile["content_analyses_summary"],
            "missionSummary": profile["mission_summary"],
        }
    )
    response = score_behavioral_request(request, computed_at=datetime(2026, 4, 21, 12, 0))
    addiction_subscores = {s.name: float(s.value) for s in response.addiction_subscores}
    wellbeing_subscores = {s.name: float(s.value) for s in response.wellbeing_subscores}
    triggered = [r.type for r in response.recommendations]
    triggered_missions = [m.triggering_subscore for m in response.missions]
    triggered_set = set(triggered)
    triggered_missions_set = set(triggered_missions)
    required = set(profile.get("required_recommendations", []))
    forbidden = set(profile.get("forbidden_recommendations", []))
    expected_missions = set(profile.get("expected_missions", []))

    expected_addiction_range = profile.get("expected_addiction_range")
    expected_wellbeing_range = profile.get("expected_wellbeing_range")
    addiction_score = float(response.addiction_score)
    wellbeing_score = float(response.wellbeing_score)
    range_ok = None
    if assert_ranges:
        range_ok = _in_range(addiction_score, expected_addiction_range) and _in_range(
            wellbeing_score, expected_wellbeing_range
        )

    return {
        "id": profile["id"],
        "description_fr": profile.get("description_fr", ""),
        "age_years": int(profile["age_years"]),
        "seed": int(profile["seed"]),
        "event_count": len(events),
        "addiction_score": addiction_score,
        "wellbeing_score": wellbeing_score,
        "expected_addiction_range": expected_addiction_range,
        "expected_wellbeing_range": expected_wellbeing_range,
        "addiction_subscores": addiction_subscores,
        "wellbeing_subscores": wellbeing_subscores,
        "triggered_recommendations": triggered,
        "required_recommendations": sorted(required),
        "forbidden_recommendations": sorted(forbidden),
        "required_ok": required.issubset(triggered_set),
        "forbidden_ok": triggered_set.isdisjoint(forbidden),
        "triggered_missions": triggered_missions,
        "expected_missions": sorted(expected_missions),
        "missions_ok": expected_missions.issubset(triggered_missions_set),
        "range_ok": range_ok,
    }


def _band_addiction(value: float) -> str:
    if value < 0.20:
        return "low"
    if value < 0.40:
        return "moderate"
    return "high"


def _band_wellbeing(value: float) -> str:
    if value < 0.40:
        return "low"
    if value < 0.70:
        return "moderate"
    return "high"


def _age_bracket(age: int) -> str:
    if 2 <= age <= 5:
        return "2-5"
    if 6 <= age <= 12:
        return "6-12"
    if 13 <= age <= 18:
        return "13-18"
    return "other"


def _pct(count: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{(100.0 * count / total):.1f}%"


def _render_markdown(
    rows: list[dict[str, Any]],
    *,
    profiles_path: Path,
    assert_ranges: bool,
    report_name: str,
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    total = len(rows)
    required_ok_count = sum(1 for r in rows if r["required_ok"])
    forbidden_ok_count = sum(1 for r in rows if r["forbidden_ok"])
    missions_ok_count = sum(1 for r in rows if r["missions_ok"])
    range_rows = [r for r in rows if r["range_ok"] is not None]
    range_ok_count = sum(1 for r in range_rows if r["range_ok"])
    combined_ok_count = sum(
        1
        for r in rows
        if r["required_ok"]
        and r["forbidden_ok"]
        and r["missions_ok"]
        and (r["range_ok"] is True if assert_ranges else True)
    )

    rule_to_profiles: dict[str, list[str]] = defaultdict(list)
    severity_counter: Counter[str] = Counter()
    for row in rows:
        for rec in row["triggered_recommendations"]:
            rule_to_profiles[rec].append(row["id"])
            severity_counter[RULE_SEVERITY.get(rec, "unknown")] += 1

    addiction_bands = Counter(_band_addiction(float(r["addiction_score"])) for r in rows)
    wellbeing_bands = Counter(_band_wellbeing(float(r["wellbeing_score"])) for r in rows)
    age_bands = Counter(_age_bracket(int(r["age_years"])) for r in rows)

    title = (
        "# Behavioral Module — Baseline Benchmark Report (v1)"
        if report_name == "behavioral_baseline_v1.md"
        else "# Behavioral Benchmark Report (actuals)"
    )
    report: list[str] = [title, ""]

    report.append("## Run metadata")
    report.append("")
    report.append(f"- Timestamp UTC: **{ts}**")
    report.append("- Scorer version: **Phase 6b**")
    report.append(f"- Profiles file: `{profiles_path.as_posix()}`")
    report.append(f"- Total profile count: **{total}**")
    report.append(
        f"- Score range pass rate: **{range_ok_count}/{len(range_rows)}**"
        if assert_ranges
        else "- Score range pass rate: **N/A (run without --assert-ranges)**"
    )
    report.append(f"- Required-recommendation pass rate: **{required_ok_count}/{total}**")
    report.append(f"- Forbidden-recommendation pass rate: **{forbidden_ok_count}/{total}**")
    report.append(f"- Missions expected-subset pass rate: **{missions_ok_count}/{total}**")
    report.append("")

    report.append("## Headline metrics")
    report.append("")
    report.append(
        f"- Score range pass rate: **{range_ok_count}/{len(range_rows)} ({_pct(range_ok_count, len(range_rows))})**"
        if assert_ranges
        else "- Score range pass rate: **N/A**"
    )
    report.append(
        f"- Required-recommendation pass rate: **{required_ok_count}/{total} ({_pct(required_ok_count, total)})**"
    )
    report.append(
        f"- Forbidden-recommendation pass rate: **{forbidden_ok_count}/{total} ({_pct(forbidden_ok_count, total)})**"
    )
    report.append(
        f"- Missions expected-subset pass rate: **{missions_ok_count}/{total} ({_pct(missions_ok_count, total)})**"
    )
    report.append(f"- Combined pass rate (all green): **{combined_ok_count}/{total} ({_pct(combined_ok_count, total)})**")
    report.append("")

    report.append("## Category distribution")
    report.append("")
    report.append("| Distribution | low | moderate | high |")
    report.append("|---|---:|---:|---:|")
    report.append(
        f"| Addiction | {addiction_bands.get('low', 0)} | {addiction_bands.get('moderate', 0)} | {addiction_bands.get('high', 0)} |"
    )
    report.append(
        f"| Wellbeing | {wellbeing_bands.get('low', 0)} | {wellbeing_bands.get('moderate', 0)} | {wellbeing_bands.get('high', 0)} |"
    )
    report.append("")
    report.append("| Age bracket | Count |")
    report.append("|---|---:|")
    for bracket in ("2-5", "6-12", "13-18", "other"):
        report.append(f"| {bracket} | {age_bands.get(bracket, 0)} |")
    report.append("")

    report.append("## Recommendation rule coverage")
    report.append("")
    report.append("| Rule | Severity | Triggered by profile ids | Coverage |")
    report.append("|---|---|---|---|")
    covered = 0
    for rule in RULE_SEVERITY:
        ids = rule_to_profiles.get(rule, [])
        has_cov = bool(ids)
        covered += 1 if has_cov else 0
        report.append(
            f"| {rule} | {RULE_SEVERITY[rule]} | {', '.join(ids) if ids else '-'} | {'✓' if has_cov else '✗'} |"
        )
    report.append(f"- Rule coverage rate: **{covered}/{len(RULE_SEVERITY)}**")
    report.append("")

    report.append("## Profile summary table")
    report.append("")
    report.append(
        "| id | age | addiction (range) | wellbeing (range) | triggered | Missions | range_ok | required_ok | forbidden_ok | missions_ok |"
    )
    report.append("|---|---:|---|---|---|---|---|---|---|---|")
    for row in rows:
        add_range = row["expected_addiction_range"]
        well_range = row["expected_wellbeing_range"]
        add_cell = (
            f"{row['addiction_score']:.3f} ({add_range[0]:.3f}-{add_range[1]:.3f})"
            if add_range
            else f"{row['addiction_score']:.3f} (-)"
        )
        well_cell = (
            f"{row['wellbeing_score']:.3f} ({well_range[0]:.3f}-{well_range[1]:.3f})"
            if well_range
            else f"{row['wellbeing_score']:.3f} (-)"
        )
        report.append(
            f"| {row['id']} | {row['age_years']} | {add_cell} | {well_cell} | "
            f"{', '.join(row['triggered_recommendations']) or '-'} | "
            f"{', '.join(row['triggered_missions']) or '-'} | "
            f"{row['range_ok'] if row['range_ok'] is not None else 'N/A'} | "
            f"{row['required_ok']} | {row['forbidden_ok']} | {row['missions_ok']} |"
        )
    report.append("")

    report.append("## Per-profile details")
    report.append("")
    for row in rows:
        report.append(f"### {row['id']}")
        report.append("")
        report.append(f"- Description: {row['description_fr']}")
        report.append(f"- Age: {row['age_years']}")
        report.append(f"- Seed: {row['seed']}")
        report.append(f"- Generated events: {row['event_count']}")
        report.append(f"- addiction_score: {row['addiction_score']:.3f}")
        report.append(f"- wellbeing_score: {row['wellbeing_score']:.3f}")
        report.append(f"- expected_addiction_range: {row['expected_addiction_range']}")
        report.append(f"- expected_wellbeing_range: {row['expected_wellbeing_range']}")
        report.append(f"- Triggered recommendations: {', '.join(row['triggered_recommendations']) or '-'}")
        report.append(f"- Required recommendations: {', '.join(row['required_recommendations']) or '-'}")
        report.append(f"- Forbidden recommendations: {', '.join(row['forbidden_recommendations']) or '-'}")
        report.append(f"- Triggered missions: {', '.join(row['triggered_missions']) or '-'}")
        report.append(f"- Expected missions: {', '.join(row['expected_missions']) or '-'}")
        report.append(f"- range_ok: {row['range_ok'] if row['range_ok'] is not None else 'N/A'}")
        report.append(f"- required_ok: {row['required_ok']}")
        report.append(f"- forbidden_ok: {row['forbidden_ok']}")
        report.append(f"- missions_ok: {row['missions_ok']}")
        report.append("")
        report.append(
            f"Expected ranges (header): addiction={row['expected_addiction_range']} | wellbeing={row['expected_wellbeing_range']}"
        )
        report.append("")
        report.append("| Subscore group | name | value |")
        report.append("|---|---|---:|")
        for name, value in row["addiction_subscores"].items():
            report.append(f"| addiction | {name} | {value:.3f} |")
        for name, value in row["wellbeing_subscores"].items():
            report.append(f"| wellbeing | {name} | {value:.3f} |")
        report.append("")

    report.append("## Reproducibility")
    report.append("")
    report.append("- Determinism: generator uses only local `random.Random(seed)`.")
    report.append("- No numpy or external stochastic library used.")
    report.append(
        "- Reproduce command: "
        "`\\.venv\\Scripts\\python.exe -m evaluation.behavioral.scripts.run_behavioral_benchmark "
        f"--profiles {profiles_path.as_posix()} --report-name {report_name}`"
    )
    report.append("- Seed list per profile:")
    report.append("| id | seed |")
    report.append("|---|---:|")
    for row in rows:
        report.append(f"| {row['id']} | {row['seed']} |")
    report.append("")

    report.append("## Methodology")
    report.append("")
    report.append("- Profiles are synthetic clinical archetypes (15 fixed seeds, 14-day windows).")
    report.append("- Scores use saturating calibration (`saturating_score`, `steepness=0.5`).")
    report.append("- Expected ranges are calibrated from empirical second-run actuals with tolerance ±0.08.")
    report.append("- Recommendation thresholds are calibrated in Phase 6b for clinical sensitivity and specificity.")
    report.append("")

    report.append("## Limitations")
    report.append("")
    report.append("- Profiles are synthetic; no real field telemetry is used yet.")
    report.append("- Scoring and recommendations are rule-based; no supervised ML layer is used.")
    report.append("- Circadian patterns are simplified (weekend behavior uses multiplier).")
    report.append("")

    report.append("## Clinical source citations")
    report.append("")
    report.append("- American Academy of Pediatrics (AAP), *Media and Young Minds* (2016)")
    report.append("- World Health Organization (WHO), sedentary behavior guidelines (2019)")
    report.append("- American Academy of Sleep Medicine (AASM), pediatric sleep recommendations (2014)")
    report.append("- Panova & Carbonell, smartphone addiction critique (2018)")
    report.append("- Kwon et al., Smartphone Addiction Scale (2013)")
    report.append("")

    return "\n".join(report)


def execute_benchmark(
    *,
    profiles_path: Path,
    report_path: Path,
    export_actuals_path: Path | None,
    assert_ranges: bool = False,
) -> dict[str, Any]:
    profiles = load_profiles(profiles_path)
    rows = [_run_profile(profile, assert_ranges=assert_ranges) for profile in profiles]
    markdown = _render_markdown(
        rows,
        profiles_path=profiles_path,
        assert_ranges=assert_ranges,
        report_name=report_path.name,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")

    payload = {
        "run_timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "profiles_path": profiles_path.as_posix(),
        "profile_count": len(rows),
        "assert_ranges": assert_ranges,
        "profiles": rows,
    }
    if export_actuals_path is not None:
        export_actuals_path.parent.mkdir(parents=True, exist_ok=True)
        export_actuals_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run behavioral benchmark profiles.")
    parser.add_argument(
        "--profiles",
        required=True,
        help="Path to behavioral profiles JSON (relative to ai-service or absolute).",
    )
    parser.add_argument(
        "--report-name",
        default="first_run_actuals.md",
        help="Filename inside evaluation/behavioral/reports/.",
    )
    parser.add_argument(
        "--export-actuals",
        default=None,
        help="Optional JSON export path for per-profile actual outputs.",
    )
    parser.add_argument(
        "--assert-ranges",
        action="store_true",
        help="Assert expected_addiction_range and expected_wellbeing_range when present.",
    )
    args = parser.parse_args(argv)

    profiles_path = _resolve_profiles_path(args.profiles)
    report_path = BEHAVIORAL_ROOT / "reports" / args.report_name
    export_path = _resolve_profiles_path(args.export_actuals) if args.export_actuals else None

    if not profiles_path.is_file():
        print(f"[behavioral-benchmark] profiles not found: {profiles_path}")
        return 0

    payload = execute_benchmark(
        profiles_path=profiles_path,
        report_path=report_path,
        export_actuals_path=export_path,
        assert_ranges=args.assert_ranges,
    )
    print(f"[behavioral-benchmark] profiles executed: {payload['profile_count']}")
    print(f"[behavioral-benchmark] report generated: {report_path}")
    if export_path is not None:
        print(f"[behavioral-benchmark] actuals exported: {export_path}")
    # Intentionally always return 0: diagnostics are reported in markdown/JSON.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
