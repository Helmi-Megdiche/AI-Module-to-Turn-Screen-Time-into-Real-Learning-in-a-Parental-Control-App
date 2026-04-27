"""Metric helpers for AI-03 text benchmark."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable


def safe_div(numerator: float, denominator: float) -> float:
    """Return numerator/denominator, guarding division by zero."""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def category_accuracy(actual: list[str], expected: list[str]) -> float:
    """Exact category accuracy over aligned arrays."""
    if len(actual) != len(expected):
        raise ValueError("actual and expected category arrays must have same length")
    if not actual:
        return 0.0
    correct = sum(1 for a, e in zip(actual, expected) if a == e)
    return safe_div(correct, len(actual))


def risk_range_ok(
    risk_score: float,
    expected_min: float | None,
    expected_max: float | None,
) -> bool | None:
    """
    Return True/False when min+max are provided, else None (not evaluated).
    """
    if expected_min is None or expected_max is None:
        return None
    return expected_min <= risk_score <= expected_max


def precision_recall_f1(
    actual_keywords_per_row: list[Iterable[str]],
    expected_keywords_per_row: list[Iterable[str]],
    label_set: Iterable[str],
) -> dict[str, dict[str, float]]:
    """
    Per-label precision/recall/F1 across rows (multi-label one-vs-rest style).
    """
    labels = list(label_set)
    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)

    for actual_row, expected_row in zip(actual_keywords_per_row, expected_keywords_per_row):
        a = set(actual_row)
        e = set(expected_row)
        for label in labels:
            in_a = label in a
            in_e = label in e
            if in_a and in_e:
                tp[label] += 1
            elif in_a and not in_e:
                fp[label] += 1
            elif (not in_a) and in_e:
                fn[label] += 1

    out: dict[str, dict[str, float]] = {}
    for label in labels:
        p = safe_div(tp[label], tp[label] + fp[label])
        r = safe_div(tp[label], tp[label] + fn[label])
        f1 = safe_div(2 * p * r, p + r)
        out[label] = {
            "precision": p,
            "recall": r,
            "f1": f1,
            "tp": float(tp[label]),
            "fp": float(fp[label]),
            "fn": float(fn[label]),
        }
    return out


def confusion_matrix(
    actual_labels: list[str],
    expected_labels: list[str],
    label_list: Iterable[str],
) -> dict[str, dict[str, int]]:
    """Return matrix[expected][actual] counts for category labels."""
    labels = list(label_list)
    matrix = {exp: {act: 0 for act in labels} for exp in labels}
    for act, exp in zip(actual_labels, expected_labels):
        if exp not in matrix:
            matrix[exp] = {k: 0 for k in labels}
        matrix[exp].setdefault(act, 0)
        matrix[exp][act] = matrix[exp].get(act, 0) + 1
    return matrix


def per_expected_category_recall(
    matrix: dict[str, dict[str, int]],
    label_list: Iterable[str],
) -> dict[str, dict[str, float | int]]:
    """
    Per expected category: row total, diagonal (correct), recall = TP / row_total.

    Aligns with confusion_matrix layout (rows = expected, columns = predicted).
    """
    labels = list(label_list)
    out: dict[str, dict[str, float | int]] = {}
    for exp in labels:
        row = matrix.get(exp, {})
        total = sum(row.values())
        tp = int(row.get(exp, 0))
        out[exp] = {
            "total": total,
            "correct": tp,
            "recall": safe_div(float(tp), float(total)),
        }
    return out
