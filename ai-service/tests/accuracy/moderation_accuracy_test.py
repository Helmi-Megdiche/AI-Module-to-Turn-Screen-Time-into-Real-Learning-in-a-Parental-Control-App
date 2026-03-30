"""
Text-only moderation accuracy via build_analyze_response_from_plain_text (no OCR).

Run from ai-service root:

  py -3 tests/accuracy/moderation_accuracy_test.py --mode simple
  py -3 tests/accuracy/moderation_accuracy_test.py --mode detailed --export results.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))


def run_eval(args: argparse.Namespace) -> dict:
    from app.services.analysis_orchestrator import build_analyze_response_from_plain_text

    from tests.accuracy.utils import (
        CATEGORY_LABELS,
        compute_latency_stats,
        confusion_matrix_counts,
        load_dataset,
        per_class_precision_recall,
        risk_calibration_ok,
    )

    dataset_path = args.dataset or (_SCRIPT_DIR / "dataset.json")
    rows = load_dataset(dataset_path)

    predicted: list[str] = []
    expected: list[str] = []
    risk_ok_flags: list[bool] = []
    latencies: list[float] = []

    per_row: list[dict] = []

    n_passes = max(1, args.n)
    for row in rows:
        text = str(row.get("input", ""))
        exp_cat = str(row.get("expected_category", "")).strip()
        if not exp_cat:
            continue
        for rep in range(n_passes):
            t0 = time.perf_counter()
            res = build_analyze_response_from_plain_text(text, image=None)
            latencies.append(time.perf_counter() - t0)
            if rep == 0:
                predicted.append(res.category)
                expected.append(exp_cat)
                rc = risk_calibration_ok(res.risk_score, row)
                if rc is not None:
                    risk_ok_flags.append(rc)
                per_row.append(
                    {
                        "id": row.get("id"),
                        "expected": exp_cat,
                        "predicted": res.category,
                        "risk": res.risk_score,
                        "category_ok": res.category == exp_cat,
                        "risk_calibration_ok": rc,
                    }
                )

    correct = sum(1 for a, e in zip(predicted, expected) if a == e)
    cat_acc = correct / len(expected) if expected else 0.0
    cal_ok = sum(1 for x in risk_ok_flags if x)
    cal_tot = len(risk_ok_flags)
    cal_rate = cal_ok / cal_tot if cal_tot else 0.0

    cm = confusion_matrix_counts(predicted, expected, CATEGORY_LABELS)
    pr = per_class_precision_recall(predicted, expected, CATEGORY_LABELS)
    lat_stats = compute_latency_stats(latencies)

    return {
        "rows": len(rows),
        "category_accuracy": cat_acc,
        "risk_calibration": {"ok": cal_ok, "total": cal_tot, "rate": cal_rate},
        "confusion_matrix": cm,
        "per_class": pr,
        "latency": lat_stats,
        "per_row": per_row,
    }


def print_simple(out: dict) -> None:
    print("MODEL ACCURACY SUMMARY")
    print("----------------------")
    print()
    print("Moderation (text -> orchestrator)")
    print(f"  Category accuracy: {out['category_accuracy']:.2f}")
    rc = out["risk_calibration"]
    if rc["total"]:
        print(f"  Risk calibration accuracy: {rc['rate']:.2f}")
    print()
    lt = out["latency"]
    print(f"Average latency: {lt['mean_s']:.2f} sec")


def print_detailed(out: dict) -> None:
    print("DETAILED REPORT")
    print("---------------")
    print()
    print("Moderation metrics")
    print("------------------")
    print(f"Rows in dataset: {out['rows']}")
    print(f"Category accuracy: {out['category_accuracy']:.3f}")
    rc = out["risk_calibration"]
    print()
    print("Risk calibration:")
    print(f"  within expected range: {rc['ok']}")
    print(f"  evaluated: {rc['total']}")
    if rc["total"]:
        print(f"  Calibration accuracy: {rc['rate']:.3f}")
    print()
    print("Confusion matrix (rows=expected, cols=predicted):")
    labels = list(out["confusion_matrix"].keys())
    header = " " * 14 + "".join(f"{c:>12}" for c in labels)
    print(header)
    for exp in labels:
        row = out["confusion_matrix"][exp]
        cells = "".join(f"{row.get(p, 0):>12}" for p in labels)
        print(f"{exp:>12}  {cells}")
    print()
    print("Per-class (one-vs-rest):")
    for cat, m in out["per_class"].items():
        print(
            f"  {cat}: precision={m['precision']:.3f} recall={m['recall']:.3f} "
            f"f1={m['f1']:.3f} TP={int(m['tp'])} FP={int(m['fp'])} FN={int(m['fn'])}"
        )
    print()
    lt = out["latency"]
    print("Latency metrics")
    print("---------------")
    print(f"median latency: {lt['median_s']:.2f} sec")
    print(f"p95 latency: {lt['p95_s']:.2f} sec")


def main() -> int:
    parser = argparse.ArgumentParser(description="Moderation / orchestrator accuracy")
    parser.add_argument("--mode", choices=("simple", "detailed"), default="simple")
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--n", type=int, default=1, help="Repeat passes (first pass records metrics)")
    parser.add_argument("--export", type=Path, default=None)
    ns = parser.parse_args()

    out = run_eval(ns)
    if ns.mode == "detailed":
        print_detailed(out)
    else:
        print_simple(out)

    if ns.export:
        ns.export.parent.mkdir(parents=True, exist_ok=True)
        export = {k: v for k, v in out.items()}
        ns.export.write_text(json.dumps(export, indent=2), encoding="utf-8")
        print(f"\nExported: {ns.export}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
