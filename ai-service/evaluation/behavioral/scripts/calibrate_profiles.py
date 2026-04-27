"""Inject expected score ranges into behavioral profiles from actual outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _resolve(path_raw: str) -> Path:
    path = Path(path_raw)
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _range_from_actual(actual: float, tolerance: float) -> list[float]:
    return [round(_clamp01(actual - tolerance), 3), round(_clamp01(actual + tolerance), 3)]


def calibrate_profiles(
    *,
    profiles_path: Path,
    actuals_path: Path,
    tolerance: float,
) -> list[dict[str, Any]]:
    profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
    actuals_payload = json.loads(actuals_path.read_text(encoding="utf-8"))
    actual_map = {
        row["id"]: {
            "addiction_score": float(row["addiction_score"]),
            "wellbeing_score": float(row["wellbeing_score"]),
        }
        for row in actuals_payload.get("profiles", [])
    }

    changes: list[dict[str, Any]] = []
    for profile in profiles:
        pid = profile["id"]
        if pid not in actual_map:
            continue
        prev_add = profile.get("expected_addiction_range")
        prev_well = profile.get("expected_wellbeing_range")
        new_add = _range_from_actual(actual_map[pid]["addiction_score"], tolerance)
        new_well = _range_from_actual(actual_map[pid]["wellbeing_score"], tolerance)
        profile["expected_addiction_range"] = new_add
        profile["expected_wellbeing_range"] = new_well
        changes.append(
            {
                "id": pid,
                "old_expected_addiction_range": prev_add,
                "new_expected_addiction_range": new_add,
                "old_expected_wellbeing_range": prev_well,
                "new_expected_wellbeing_range": new_well,
            }
        )

    profiles_path.write_text(
        json.dumps(profiles, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calibrate expected score ranges from actuals.")
    parser.add_argument("--profiles", required=True, help="Path to behavioral_profiles_v1.json")
    parser.add_argument("--actuals", required=True, help="Path to benchmark JSON actuals export")
    parser.add_argument("--tolerance", type=float, default=0.08, help="Half-width tolerance")
    args = parser.parse_args(argv)

    profiles_path = _resolve(args.profiles)
    actuals_path = _resolve(args.actuals)
    changes = calibrate_profiles(
        profiles_path=profiles_path,
        actuals_path=actuals_path,
        tolerance=float(args.tolerance),
    )
    print(f"[calibrate-profiles] updated profiles: {len(changes)}")
    for change in changes:
        print(
            f"- {change['id']}: "
            f"add {change['old_expected_addiction_range']} -> {change['new_expected_addiction_range']} | "
            f"well {change['old_expected_wellbeing_range']} -> {change['new_expected_wellbeing_range']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
