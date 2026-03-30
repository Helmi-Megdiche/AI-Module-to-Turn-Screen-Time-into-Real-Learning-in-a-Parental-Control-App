"""
Optional OCR latency benchmark (not run in default pytest collection).

Run from ai-service root:

  py -3 tests/ocr_latency_test.py --image path/to/screenshot.png --n 20

Requires EasyOCR and GPU/CPU stack available for the readers.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

# Make `app.*` importable when running from ai-service root.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


def _percentile(sorted_times: list[float], p: float) -> float:
    if not sorted_times:
        return 0.0
    k = max(0, min(len(sorted_times) - 1, int(round(p * (len(sorted_times) - 1)))))
    return sorted_times[k]


def benchmark_one(image_path: Path, n: int) -> None:
    from PIL import Image

    from app.services import ocr_service

    img = Image.open(image_path).convert("RGB")
    times: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        ocr_service.extract_text(img)
        times.append(time.perf_counter() - t0)
    times.sort()
    med = statistics.median(times)
    p95 = _percentile(times, 0.95)
    print(f"image={image_path.name} n={n} median_s={med:.3f} p95_s={p95:.3f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure extract_text() latency.")
    parser.add_argument(
        "--image",
        action="append",
        dest="images",
        required=True,
        help="Path to screenshot (repeat for multiple).",
    )
    parser.add_argument("--n", type=int, default=20, help="Iterations per image (default 20).")
    args = parser.parse_args()

    for raw in args.images:
        p = Path(raw).expanduser().resolve()
        if not p.is_file():
            print(f"Not a file: {p}", file=sys.stderr)
            return 1
        benchmark_one(p, max(1, args.n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
