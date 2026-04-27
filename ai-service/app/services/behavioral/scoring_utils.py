from __future__ import annotations

import math


def saturating_score(value: float, inflection: float, steepness: float = 0.5) -> float:
    """
    Monotone smooth [0,1] mapping using exponential saturation.
    f(0) = 0
    f(inflection)   ~= 0.39  (yellow zone -- clinical threshold reached)
    f(2*inflection) ~= 0.63  (amber)
    f(3*inflection) ~= 0.78  (orange)
    f(5*inflection) ~= 0.92  (red -- far above clinical)
    f(+infinity)    -> 1.0
    Formula: 1 - exp(-steepness * value / inflection).
    """
    if inflection <= 0 or value <= 0:
        return 0.0
    ratio = value / inflection
    return min(1.0, 1.0 - math.exp(-steepness * ratio))


def inverse_score(harm_score: float) -> float:
    """Map harm [0,1] to wellness equivalent: 1 - harm, clamped."""
    return max(0.0, min(1.0, 1.0 - harm_score))


def weighted_global(subscores: dict[str, float], weights: dict[str, float]) -> float:
    """Weighted sum; keys must match exactly; result rounded to 3 decimals."""
    total = 0.0
    for name, value in subscores.items():
        total += weights[name] * value
    return round(max(0.0, min(1.0, total)), 3)
