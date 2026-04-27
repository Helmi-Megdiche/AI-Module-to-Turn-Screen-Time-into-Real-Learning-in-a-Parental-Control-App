from __future__ import annotations

import math

import pytest

from app.services.behavioral.scoring_utils import inverse_score, saturating_score, weighted_global


def test_saturating_score_zero_cases():
    assert saturating_score(0.0, 10.0) == 0.0
    assert saturating_score(10.0, 0.0) == 0.0
    assert saturating_score(-1.0, 10.0) == 0.0


def test_saturating_score_monotone():
    a = saturating_score(20.0, 60.0)
    b = saturating_score(60.0, 60.0)
    c = saturating_score(120.0, 60.0)
    assert 0.0 < a < b < c <= 1.0


def test_saturating_score_matches_doc_shape():
    # f(inflection) ~= 1 - exp(-0.5) = 0.3934
    assert saturating_score(50.0, 50.0) == pytest.approx(1.0 - math.exp(-0.5), rel=1e-6)


def test_saturating_score_clinical_thresholds():
    inflection = 100.0
    assert 0.35 < saturating_score(inflection, inflection) < 0.45
    assert 0.60 < saturating_score(2 * inflection, inflection) < 0.70
    assert 0.75 < saturating_score(3 * inflection, inflection) < 0.82
    assert 0.88 < saturating_score(5 * inflection, inflection) < 0.95


def test_inverse_score_clamps():
    assert inverse_score(0.0) == 1.0
    assert inverse_score(1.0) == 0.0
    assert inverse_score(1.4) == 0.0
    assert inverse_score(-0.5) == 1.0


def test_weighted_global_rounds_and_clamps():
    subscores = {"a": 0.3333, "b": 0.6666}
    weights = {"a": 0.4, "b": 0.6}
    assert weighted_global(subscores, weights) == 0.533


def test_weighted_global_requires_key_match():
    with pytest.raises(KeyError):
        weighted_global({"a": 0.5}, {"b": 1.0})
