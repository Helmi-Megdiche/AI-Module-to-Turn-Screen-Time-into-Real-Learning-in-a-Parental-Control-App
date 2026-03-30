"""Shared helpers for OCR / moderation / pipeline accuracy scripts."""

from __future__ import annotations

import json
import math
import re
import statistics
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# API categories from analysis orchestrator
CATEGORY_LABELS = ("safe", "risky", "dangerous", "educational")


def tokenize_text(text: str) -> list[str]:
    """Lowercase tokens; strip punctuation boundaries; keep Arabic and Latin word chars."""
    if not text:
        return []
    return [t.lower() for t in re.findall(r"[\w']+", text, flags=re.UNICODE) if t.strip()]


def load_dataset(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("dataset must be a JSON array")
    return data


def compute_word_accuracy(expected_tokens: list[str], actual_tokens: list[str]) -> tuple[int, int, float]:
    """
    Word recall of expected tokens against actual (set membership, unique expected order).

    Returns:
        (hits, n_expected_unique, rate) where rate = hits / n_expected_unique or 1.0 if empty.
    """
    seen_exp: list[str] = []
    for w in expected_tokens:
        if w not in seen_exp:
            seen_exp.append(w)
    if not seen_exp:
        return 0, 0, 1.0
    actual_set = set(actual_tokens)
    hits = sum(1 for w in seen_exp if w in actual_set)
    n = len(seen_exp)
    return hits, n, hits / n


def confusion_matrix_counts(
    predicted: list[str],
    expected: list[str],
    labels: tuple[str, ...] = CATEGORY_LABELS,
) -> dict[str, dict[str, int]]:
    """matrix[expected_row][predicted_column] counts."""
    matrix: dict[str, dict[str, int]] = {e: dict.fromkeys(labels, 0) for e in labels}
    for pred, exp in zip(predicted, expected):
        if exp not in matrix:
            matrix[exp] = dict.fromkeys(labels, 0)
        matrix[exp].setdefault(pred, 0)
        matrix[exp][pred] = matrix[exp].get(pred, 0) + 1
    return matrix


def per_class_precision_recall(
    predicted: list[str],
    expected: list[str],
    labels: tuple[str, ...] = CATEGORY_LABELS,
) -> dict[str, dict[str, float]]:
    """One-vs-rest precision, recall, F1 per category label."""
    out: dict[str, dict[str, float]] = {}
    for cat in labels:
        tp = sum(1 for p, e in zip(predicted, expected) if p == cat and e == cat)
        fp = sum(1 for p, e in zip(predicted, expected) if p == cat and e != cat)
        fn = sum(1 for p, e in zip(predicted, expected) if p != cat and e == cat)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        out[cat] = {"precision": prec, "recall": rec, "f1": f1, "tp": float(tp), "fp": float(fp), "fn": float(fn)}
    return out


def compute_latency_stats(seconds: list[float]) -> dict[str, float]:
    """median and p95 in seconds."""
    if not seconds:
        return {"median_s": 0.0, "p95_s": 0.0, "mean_s": 0.0}
    s = sorted(seconds)
    n = len(s)

    def _p(p: float) -> float:
        if n == 1:
            return s[0]
        idx = min(n - 1, max(0, int(math.ceil(p * n) - 1)))
        return s[idx]

    return {
        "median_s": float(statistics.median(s)),
        "p95_s": float(_p(0.95)),
        "mean_s": float(statistics.mean(s)),
    }


def text_to_screenshot_image(
    text: str,
    width: int = 960,
    pad: int = 24,
    max_height: int = 2000,
) -> Image.Image:
    """
    Render plain text to a synthetic RGB image for OCR evaluation (no external assets).

    Uses default bitmap font; line-wraps on whitespace.
    """
    text = (text or "").strip() or " "
    img = Image.new("RGB", (width, max_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    x0, y0 = pad, pad
    line_h = 16
    try:
        bbox = draw.textbbox((0, 0), "Ag", font=font)
        line_h = bbox[3] - bbox[1] + 4
    except Exception:
        line_h = 16

    y = y0
    max_x = width - pad
    for paragraph in text.split("\n"):
        words = paragraph.split()
        line = ""
        for w in words:
            trial = (line + " " + w).strip()
            try:
                bbox = draw.textbbox((0, 0), trial, font=font)
                tw = bbox[2] - bbox[0]
            except Exception:
                tw = len(trial) * 6
            if x0 + tw > max_x and line:
                draw.text((x0, y), line, fill=(0, 0, 0), font=font)
                y += line_h
                line = w
            else:
                line = trial
        if line:
            draw.text((x0, y), line, fill=(0, 0, 0), font=font)
            y += line_h
        y += line_h // 2

    crop_h = min(max_height, y + pad)
    return img.crop((0, 0, width, crop_h))


def risk_calibration_ok(risk: float, row: dict[str, Any]) -> bool | None:
    """True/False when bounds exist; None if no risk expectation in row."""
    mn = row.get("expected_risk_min")
    mx = row.get("expected_risk_max")
    if mn is None and mx is None:
        return None
    if mn is not None and mx is not None:
        return float(mn) <= risk <= float(mx)
    if mn is not None:
        return risk >= float(mn)
    return risk <= float(mx)


def resolve_image_path(row: dict[str, Any], images_dir: Path | None) -> Path | None:
    """Return path for type=image rows; `image` field relative to images_dir or absolute."""
    if str(row.get("type", "")).lower() != "image":
        return None
    ref = row.get("image") or row.get("input") or row.get("path")
    if not ref:
        return None
    p = Path(str(ref))
    if p.is_absolute():
        return p if p.is_file() else None
    if images_dir is not None:
        cand = images_dir / p
        return cand if cand.is_file() else None
    return None
