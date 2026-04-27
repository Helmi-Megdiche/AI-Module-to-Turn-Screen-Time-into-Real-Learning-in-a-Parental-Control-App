"""Run AI-03 benchmark against text-only orchestration."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

# Make `app.*` importable when running from ai-service root.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import config
from app.services.analysis_orchestrator import build_analyze_response_from_plain_text
from evaluation.scripts.compute_metrics import (
    category_accuracy,
    confusion_matrix,
    per_expected_category_recall,
    precision_recall_f1,
    risk_range_ok,
    safe_div,
)


ROOT = Path(__file__).parent.parent


def load_dataset(dataset_path: Path) -> list[dict[str, Any]]:
    with dataset_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Dataset must be a JSON array")
    return data


def _row_expected_category(row: dict[str, Any]) -> str:
    v = row.get("expectedCategory")
    if v is not None and str(v).strip():
        return str(v).strip()
    v = row.get("expected_category")
    return str(v).strip() if v is not None else ""


def _row_expected_risk_bounds(row: dict[str, Any]) -> tuple[Any, Any]:
    mn = row.get("expectedRiskMin")
    if mn is None:
        mn = row.get("expected_risk_min")
    mx = row.get("expectedRiskMax")
    if mx is None:
        mx = row.get("expected_risk_max")
    return mn, mx


def _row_expected_labels(row: dict[str, Any]) -> list[str]:
    labs = row.get("expectedLabels")
    if labs is None:
        labs = row.get("expected_labels")
    if labs is not None:
        return [str(x) for x in list(labs)]
    return []


def _row_expected_educational_bool(row: dict[str, Any]) -> bool | None:
    if "expectedEducational" in row:
        v = row["expectedEducational"]
        return bool(v) if v is not None else None
    if "expected_educational" in row:
        v = row["expected_educational"]
        return bool(v) if v is not None else None
    return None


def _row_expected_educational_bounds(row: dict[str, Any]) -> tuple[Any, Any]:
    mn = row.get("expectedEducationalMin")
    if mn is None:
        mn = row.get("expected_educational_min")
    mx = row.get("expectedEducationalMax")
    if mx is None:
        mx = row.get("expected_educational_max")
    return mn, mx


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def _short(text: str, limit: int = 100) -> str:
    text = (text or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _bool_eval(
    got: bool,
    expected: bool | None,
) -> bool | None:
    if expected is None:
        return None
    return got == expected


def _failure_reasons(rec: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if rec.get("categoryOk") is False:
        reasons.append(
            f"category: expected {rec.get('expectedCategory')!r} got {rec.get('actualCategory')!r}"
        )
    if rec.get("riskOk") is False:
        reasons.append(
            f"risk: {rec.get('actualRisk'):.2f} not in [{rec.get('expectedRiskMin')}, {rec.get('expectedRiskMax')}]"
        )
    return reasons


def run() -> int:
    parser = argparse.ArgumentParser(description="Run AI benchmark and generate markdown report.")
    parser.add_argument(
        "--dataset",
        default=None,
        help=(
            "Path to benchmark JSON under evaluation/ (e.g. datasets/benchmark_v3.json) "
            "or prefixed with evaluation/ when cwd is ai-service. "
            "If omitted: --hard uses hard_cases_v1.json; else benchmark_v1.json."
        ),
    )
    parser.add_argument(
        "--hard",
        action="store_true",
        help="Use datasets/hard_cases_v1.json (unless --dataset is set).",
    )
    parser.add_argument(
        "--report-name",
        default=None,
        help="Output report filename inside evaluation/reports/ (overrides mode default).",
    )
    parser.add_argument(
        "--changes-note",
        default="",
        help="Optional short note added under a 'Changes from v1' section.",
    )
    parser.add_argument(
        "--max-failure-rows",
        type=int,
        default=0,
        help="Cap rows in the Failure Examples markdown table (0 = all failures).",
    )
    parser.add_argument(
        "--export-failures",
        type=Path,
        default=None,
        help="Write JSON with every category/risk failure (full per-sample fields + reasons).",
    )
    args = parser.parse_args()

    if args.dataset:
        ds = Path(str(args.dataset).replace("\\", "/").strip())
        if ds.is_absolute():
            dataset_path = ds
        else:
            rel = str(ds).lstrip("/")
            if rel.startswith("evaluation/"):
                rel = rel[len("evaluation/") :]
            dataset_path = ROOT / rel
        default_report_name = "baseline.md"
    elif args.hard:
        dataset_path = ROOT / "datasets" / "hard_cases_v1.json"
        default_report_name = "baseline_hard_v1.md"
    else:
        dataset_path = ROOT / "datasets" / "benchmark_v1.json"
        default_report_name = "baseline_v1.md"

    report_name = args.report_name if args.report_name is not None else default_report_name
    report_path = ROOT / "reports" / report_name

    if not dataset_path.is_file():
        raise SystemExit(f"[benchmark] dataset not found: {dataset_path}")

    rows = load_dataset(dataset_path)

    per_row: list[dict[str, Any]] = []
    all_actual_cats: list[str] = []
    all_expected_cats: list[str] = []
    all_actual_keywords: list[list[str]] = []
    all_expected_keywords: list[list[str]] = []

    for row in rows:
        text = str(row.get("text", ""))
        result = build_analyze_response_from_plain_text(text, image=None)

        expected_cat = _row_expected_category(row)
        expected_labels = _row_expected_labels(row)
        expected_min, expected_max = _row_expected_risk_bounds(row)
        expected_edu_bool = _row_expected_educational_bool(row)
        expected_edu_min, expected_edu_max = _row_expected_educational_bounds(row)

        cat_ok = result.category == expected_cat if expected_cat else None
        risk_ok = risk_range_ok(result.risk_score, expected_min, expected_max)
        edu_bool_actual = result.educational_score >= config.EDUCATIONAL_THRESHOLD
        edu_bool_ok = _bool_eval(edu_bool_actual, expected_edu_bool)
        edu_range_ok_flag = risk_range_ok(result.educational_score, expected_edu_min, expected_edu_max)

        item = {
            "id": row.get("id", ""),
            "language": row.get("language", ""),
            "slice": row.get("slice", ""),
            "text": text,
            "expectedCategory": expected_cat,
            "actualCategory": result.category,
            "categoryOk": cat_ok,
            "expectedLabels": expected_labels,
            "actualLabels": list(result.matched_keywords),
            "expectedRiskMin": expected_min,
            "expectedRiskMax": expected_max,
            "actualRisk": float(result.risk_score),
            "riskOk": risk_ok,
            "expectedEducational": expected_edu_bool,
            "actualEducationalFlag": edu_bool_actual,
            "educationalBoolOk": edu_bool_ok,
            "expectedEducationalMin": expected_edu_min,
            "expectedEducationalMax": expected_edu_max,
            "actualEducationalScore": float(result.educational_score),
            "educationalRangeOk": edu_range_ok_flag,
        }
        per_row.append(item)

        if expected_cat:
            all_expected_cats.append(expected_cat)
            all_actual_cats.append(result.category)
        all_expected_keywords.append(expected_labels)
        all_actual_keywords.append(list(result.matched_keywords))

    # Aggregate metrics
    cat_acc = category_accuracy(all_actual_cats, all_expected_cats)

    risk_rows_e = [r for r in per_row if r["riskOk"] is not None]
    risk_ok_count = sum(1 for r in risk_rows_e if r["riskOk"])
    risk_acc = safe_div(risk_ok_count, len(risk_rows_e))

    edu_range_rows = [r for r in per_row if r["educationalRangeOk"] is not None]
    edu_range_ok_count = sum(1 for r in edu_range_rows if r["educationalRangeOk"])
    edu_range_acc = safe_div(edu_range_ok_count, len(edu_range_rows))

    edu_bool_rows = [r for r in per_row if r["educationalBoolOk"] is not None]
    edu_bool_ok_count = sum(1 for r in edu_bool_rows if r["educationalBoolOk"])
    edu_bool_acc = safe_div(edu_bool_ok_count, len(edu_bool_rows))

    label_set = sorted({lab for labs in all_expected_keywords for lab in labs})
    label_metrics = precision_recall_f1(all_actual_keywords, all_expected_keywords, label_set)

    category_labels = ["safe", "risky", "dangerous", "educational"]
    cat_matrix = confusion_matrix(all_actual_cats, all_expected_cats, category_labels)
    per_cat_recall = per_expected_category_recall(cat_matrix, category_labels)

    dialect_rows = [r for r in per_row if "tunisian_dialect_risk" in set(r["expectedLabels"])]
    dialect_hits = sum(1 for r in dialect_rows if "tunisian_dialect_risk" in set(r["actualLabels"]))
    dialect_recall = safe_div(dialect_hits, len(dialect_rows))

    edu_expected_true_rows = [r for r in per_row if r["expectedEducational"] is True]
    edu_expected_true_hits = sum(1 for r in edu_expected_true_rows if r["actualEducationalFlag"] is True)
    edu_true_recall = safe_div(edu_expected_true_hits, len(edu_expected_true_rows))

    failures = [
        r
        for r in per_row
        if (r["categoryOk"] is False) or (r["riskOk"] is False)
    ]
    preview_limit = args.max_failure_rows
    failures_md = failures if preview_limit <= 0 else failures[:preview_limit]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    report_label = Path(report_name).stem.replace("_", " ")
    report: list[str] = []
    report.append(f"# AI Benchmark Report ({report_label})")
    report.append("")
    report.append(f"- Run timestamp: **{ts}**")
    report.append(f"- Dataset: `{dataset_path.as_posix()}`")
    report.append(f"- Total samples: **{len(per_row)}**")
    report.append("- Mode: `build_analyze_response_from_plain_text(text, image=None)`")
    report.append("- Thresholds:")
    report.append(f"  - `RISKY_THRESHOLD={config.RISKY_THRESHOLD}`")
    report.append(f"  - `DANGEROUS_THRESHOLD={config.DANGEROUS_THRESHOLD}`")
    report.append(f"  - `EDUCATIONAL_THRESHOLD={config.EDUCATIONAL_THRESHOLD}`")
    report.append("")

    report.append("## Summary Metrics")
    report.append("")
    report.append("| Metric | Value | Numerator/Denominator |")
    report.append("|---|---:|---:|")
    report.append(f"| Category accuracy | {_pct(cat_acc)} | {sum(1 for r in per_row if r['categoryOk'])}/{len(all_expected_cats)} |")
    report.append(f"| Risk-range pass rate | {_pct(risk_acc)} | {risk_ok_count}/{len(risk_rows_e)} |")
    report.append(f"| Educational-range pass rate | {_pct(edu_range_acc)} | {edu_range_ok_count}/{len(edu_range_rows)} |")
    report.append(f"| Educational-boolean accuracy | {_pct(edu_bool_acc)} | {edu_bool_ok_count}/{len(edu_bool_rows)} |")
    report.append(f"| Dialect subset recall (`tunisian_dialect_risk`) | {_pct(dialect_recall)} | {dialect_hits}/{len(dialect_rows)} |")
    report.append(f"| Educational positive recall | {_pct(edu_true_recall)} | {edu_expected_true_hits}/{len(edu_expected_true_rows)} |")
    report.append("")

    report.append("## Category Confusion Matrix")
    report.append("")
    report.append("Rows = expected, Columns = actual (predicted)")
    report.append("")
    header = "| expected \\ actual | " + " | ".join(category_labels) + " |"
    sep = "|---|" + "---:|" * len(category_labels)
    report.append(header)
    report.append(sep)
    for exp in category_labels:
        vals = [str(cat_matrix.get(exp, {}).get(act, 0)) for act in category_labels]
        report.append(f"| {exp} | " + " | ".join(vals) + " |")
    report.append("")

    report.append("## Per-Expected-Category Recall (row-normalized)")
    report.append("")
    report.append("Fraction of samples with that expected label classified with the same actual label.")
    report.append("")
    report.append("| Expected | Count | Correct (diagonal) | Recall |")
    report.append("|---|---:|---:|---:|")
    for exp in category_labels:
        m = per_cat_recall[exp]
        report.append(
            f"| {exp} | {int(m['total'])} | {int(m['correct'])} | {_pct(float(m['recall']))} |"
        )
    report.append("")

    report.append("## Per-Label Metrics (Keyword)")
    report.append("")
    report.append("| Label | Precision | Recall | F1 | TP | FP | FN |")
    report.append("|---|---:|---:|---:|---:|---:|---:|")
    for label in label_set:
        m = label_metrics[label]
        report.append(
            f"| {label} | {_pct(m['precision'])} | {_pct(m['recall'])} | {_pct(m['f1'])} | "
            f"{int(m['tp'])} | {int(m['fp'])} | {int(m['fn'])} |"
        )
    report.append("")

    report.append("## Failure Examples (category or risk range)")
    report.append("")
    if not failures:
        report.append("No category/risk-range failures found.")
    else:
        report.append(f"Total failures: **{len(failures)}**" + (f" (showing first **{len(failures_md)}** in table)" if len(failures_md) < len(failures) else ""))
        report.append("")
        report.append("| ID | Text Snippet | Expected Category | Actual Category | Expected Risk Range | Actual Risk | Expected Labels | Actual Labels |")
        report.append("|---|---|---|---|---|---:|---|---|")
        for f in failures_md:
            exp_range = f"{f['expectedRiskMin']}..{f['expectedRiskMax']}"
            report.append(
                f"| {f['id']} | {_short(f['text'])} | {f['expectedCategory']} | {f['actualCategory']} | "
                f"{exp_range} | {f['actualRisk']:.2f} | {', '.join(f['expectedLabels'])} | {', '.join(f['actualLabels'])} |"
            )
        if len(failures_md) < len(failures):
            report.append("")
            report.append(f"*Use `--max-failure-rows 0` to include all **{len(failures)}** rows in this table, or `--export-failures` for JSON.*")
    report.append("")

    report.append("## Next Steps")
    report.append("")
    report.append("- Increase hard negative samples for educational false positives.")
    report.append("- Expand Arabizi/Tunisian dialect variations to test recall stability.")
    report.append("- Add per-slice trend reports (`safe`, `educational`, `dialect`, `ocr-noisy`) in benchmark_v2.")
    report.append("")

    if args.changes_note.strip():
        report.append("## Changes from v1")
        report.append("")
        report.append(args.changes_note.strip().replace("\\n", "\n"))
        report.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(f"[benchmark] report generated: {report_path}")

    if args.export_failures is not None:
        export_payload = {
            "run_timestamp_utc": ts,
            "dataset": dataset_path.as_posix(),
            "failure_count": len(failures),
            "failures": [
                {**{k: v for k, v in rec.items()}, "reasons": _failure_reasons(rec)}
                for rec in failures
            ],
        }
        fail_path = args.export_failures
        fail_path = Path(fail_path)
        if not fail_path.is_absolute():
            fail_path = ROOT / fail_path
        fail_path.parent.mkdir(parents=True, exist_ok=True)
        fail_path.write_text(json.dumps(export_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[benchmark] failures exported: {fail_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
