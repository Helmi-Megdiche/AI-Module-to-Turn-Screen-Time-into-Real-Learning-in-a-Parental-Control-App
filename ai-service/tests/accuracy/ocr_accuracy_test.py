"""
OCR word-level accuracy (Word Accuracy Rate) against dataset ground-truth tokens.

Run from ai-service root:

  py -3 tests/accuracy/ocr_accuracy_test.py --mode simple
  py -3 tests/accuracy/ocr_accuracy_test.py --mode detailed --dataset tests/accuracy/dataset.json

For type=text, renders synthetic images via tests/accuracy/utils.text_to_screenshot_image.
For type=image, loads files under --images (or absolute paths in dataset).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))


def _expected_words(row: dict) -> list[str]:
    from tests.accuracy.utils import tokenize_text

    ew = row.get("expected_words")
    if isinstance(ew, list):
        return [str(t).lower() for t in ew]
    if isinstance(ew, str) and ew.strip():
        return tokenize_text(ew)
    return tokenize_text(str(row.get("input", "")))


def _image_for_row(row: dict, images_dir: Path | None):
    from PIL import Image

    from tests.accuracy.utils import resolve_image_path, text_to_screenshot_image

    p = resolve_image_path(row, images_dir)
    if p is not None:
        return Image.open(p).convert("RGB")
    if str(row.get("type", "")).lower() == "text":
        return text_to_screenshot_image(str(row.get("input", "")))
    return None


def run_eval(args: argparse.Namespace) -> dict:
    from app.services import ocr_service

    from tests.accuracy.utils import compute_latency_stats, compute_word_accuracy, load_dataset, tokenize_text

    dataset_path = args.dataset or (_SCRIPT_DIR / "dataset.json")
    rows = load_dataset(dataset_path)
    images_dir = args.images

    lang_hits: dict[str, list[float]] = defaultdict(list)
    total_hits = 0
    total_exp = 0
    latencies: list[float] = []
    skipped = 0

    per_row: list[dict] = []

    for row in rows:
        img = _image_for_row(row, images_dir)
        if img is None:
            skipped += 1
            continue
        lang = str(row.get("language", "unknown") or "unknown").upper()

        t0 = time.perf_counter()
        ocr_str = ocr_service.extract_text(img)
        latencies.append(time.perf_counter() - t0)

        actual_tokens = tokenize_text(ocr_str)
        exp_tokens = _expected_words(row)
        hits, nexp, rate = compute_word_accuracy(exp_tokens, actual_tokens)
        total_hits += hits
        total_exp += nexp
        lang_hits[lang].append(rate)
        per_row.append(
            {
                "id": row.get("id"),
                "language": lang,
                "war": rate,
                "expected_n": nexp,
                "hits": hits,
                "ocr_raw_sample": ocr_str[:120],
            }
        )

    # optional repeats for smoother latency (same dataset, re-run OCR)
    for _ in range(max(0, args.n - 1)):
        for row in rows:
            img = _image_for_row(row, images_dir)
            if img is None:
                continue
            t0 = time.perf_counter()
            ocr_service.extract_text(img)
            latencies.append(time.perf_counter() - t0)

    global_war = (total_hits / total_exp) if total_exp else 0.0
    lang_avg = {k: sum(v) / len(v) if v else 0.0 for k, v in sorted(lang_hits.items())}
    lat_stats = compute_latency_stats(latencies)

    return {
        "total_rows": len(rows),
        "evaluated": len(per_row),
        "skipped": skipped,
        "global_war": global_war,
        "lang_war": lang_avg,
        "latency": lat_stats,
        "per_row": per_row,
    }


def print_simple(out: dict) -> None:
    print("MODEL ACCURACY SUMMARY")
    print("----------------------")
    print()
    print("OCR (Word Accuracy Rate)")
    for lang, rate in out["lang_war"].items():
        print(f"  {lang}: {rate:.2f}")
    print(f"  Global: {out['global_war']:.2f}")
    print()
    lt = out["latency"]
    print(f"Average latency (OCR only): {lt['mean_s']:.2f} sec")


def print_detailed(out: dict) -> None:
    print("DETAILED REPORT")
    print("---------------")
    print()
    print("OCR metrics")
    print("-----------")
    print(f"Total samples: {out['total_rows']}")
    print(f"Evaluated: {out['evaluated']} (skipped: {out['skipped']})")
    hits = sum(r["hits"] for r in out["per_row"])
    exp = sum(r["expected_n"] for r in out["per_row"])
    print(f"Correct words (unique expected hit): {hits}")
    print(f"Total expected words (unique): {exp}")
    print(f"Word Accuracy Rate (global): {out['global_war']:.3f}")
    print()
    print("Accuracy per language:")
    for lang, rate in out["lang_war"].items():
        print(f"  {lang}: {rate:.3f}")
    print()
    lt = out["latency"]
    print("Latency metrics")
    print("---------------")
    print(f"median latency: {lt['median_s']:.2f} sec")
    print(f"p95 latency: {lt['p95_s']:.2f} sec")
    print()
    print("Per-row WAR (sample):")
    for r in out["per_row"][:15]:
        print(f"  {r['id']}: war={r['war']:.2f} | ocr~ {r['ocr_raw_sample']!r}")
    if len(out["per_row"]) > 15:
        print(f"  ... ({len(out['per_row']) - 15} more)")


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR word accuracy evaluation")
    parser.add_argument("--mode", choices=("simple", "detailed"), default="simple")
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--images", type=Path, default=None)
    parser.add_argument("--n", type=int, default=1, help="Extra full passes for latency stats")
    parser.add_argument("--export", type=Path, default=None)
    ns = parser.parse_args()

    out = run_eval(ns)
    if ns.mode == "detailed":
        print_detailed(out)
    else:
        print_simple(out)

    if ns.export:
        ns.export.parent.mkdir(parents=True, exist_ok=True)
        serializable = {k: v for k, v in out.items() if k != "per_row"}
        serializable["per_row"] = out["per_row"]
        ns.export.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
        print(f"\nExported: {ns.export}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
