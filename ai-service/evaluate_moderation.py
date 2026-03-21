from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

from app.services.moderation_service import moderate

DATASET_PATH = Path(__file__).with_name("moderation_eval_dataset.json")


def _within_range(score: float, low: float, high: float) -> bool:
    return low <= score <= high


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline moderation evaluation over moderation_eval_dataset.json")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any fallback flag mismatches or the flagship hate-speech case regresses",
    )
    args = parser.parse_args(argv)

    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    rows = []

    for case in cases:
        result = moderate(case["text"])
        expected_labels = set(case.get("expectedLabels", []))
        actual_labels = set(result.matched_keywords)

        row = {
            "id": case["id"],
            "expected_category": case["expectedCategory"],
            "actual_category": result.category,
            "category_ok": result.category == case["expectedCategory"],
            "expected_range": (case["expectedRiskMin"], case["expectedRiskMax"]),
            "actual_risk": result.risk_score,
            "range_ok": _within_range(
                result.risk_score,
                case["expectedRiskMin"],
                case["expectedRiskMax"],
            ),
            "expected_labels": sorted(expected_labels),
            "actual_labels": sorted(actual_labels),
            "missing_labels": sorted(expected_labels - actual_labels),
            "extra_labels": sorted(actual_labels - expected_labels),
            "expected_fallback": bool(case.get("expectFallback", False)),
            "actual_fallback": result.used_fallback,
            "fallback_ok": result.used_fallback == bool(case.get("expectFallback", False)),
            "inference_ms": result.inference_ms,
        }
        rows.append(row)

    print("=== Moderation evaluation ===")
    for row in rows:
        print(f"\n[{row['id']}]")
        print(
            f"category: {row['actual_category']} "
            f"(expected {row['expected_category']}) "
            f"=> {'OK' if row['category_ok'] else 'MISMATCH'}"
        )
        print(
            f"risk: {row['actual_risk']:.2f} "
            f"(expected range {row['expected_range'][0]:.2f}-{row['expected_range'][1]:.2f}) "
            f"=> {'OK' if row['range_ok'] else 'OUT_OF_RANGE'}"
        )
        print(f"labels: {row['actual_labels']} (expected {row['expected_labels']})")
        if row["missing_labels"] or row["extra_labels"]:
            print(
                f"label diff: missing={row['missing_labels']} extra={row['extra_labels']}"
            )
        print(
            f"fallback: {row['actual_fallback']} "
            f"(expected {row['expected_fallback']}) "
            f"=> {'OK' if row['fallback_ok'] else 'MISMATCH'}"
        )
        print(f"inference_ms: {row['inference_ms']:.2f}")

    total = len(rows)
    category_ok = sum(1 for row in rows if row["category_ok"])
    range_ok = sum(1 for row in rows if row["range_ok"])
    fallback_ok = sum(1 for row in rows if row["fallback_ok"])
    label_exact = sum(
        1
        for row in rows
        if not row["missing_labels"] and not row["extra_labels"]
    )
    timings = [row["inference_ms"] for row in rows if row["inference_ms"] > 0]

    print("\n=== Summary ===")
    print(f"cases: {total}")
    print(f"category_ok: {category_ok}/{total}")
    print(f"risk_range_ok: {range_ok}/{total}")
    print(f"fallback_ok: {fallback_ok}/{total}")
    print(f"label_exact: {label_exact}/{total}")
    if timings:
        ordered = sorted(timings)
        p95_index = max(0, min(len(ordered) - 1, int(len(ordered) * 0.95) - 1))
        print(f"avg_inference_ms: {mean(timings):.2f}")
        print(f"p95_inference_ms: {ordered[p95_index]:.2f}")

    if args.strict:
        if fallback_ok < total:
            print("STRICT: expected fallback flag mismatch for one or more cases", file=sys.stderr)
            return 1
        flagship = next((r for r in rows if r["id"] == "danger-fr-en-hate-mixed"), None)
        if flagship is None:
            print("STRICT: dataset missing id danger-fr-en-hate-mixed", file=sys.stderr)
            return 1
        if flagship["actual_category"] != "dangerous" or flagship["actual_risk"] < 0.85:
            print(
                f"STRICT: flagship hate-speech case regression (category={flagship['actual_category']!r}, risk={flagship['actual_risk']})",
                file=sys.stderr,
            )
            return 1
        if "hate speech" not in set(flagship["actual_labels"]):
            print("STRICT: flagship case missing 'hate speech' in matched labels", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
