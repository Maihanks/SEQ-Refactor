"""Unit tests for eval/random_study.py (Working Brief Phase 2c §3)."""

from __future__ import annotations

from seqrefactor.datasets import graph_from_manifest, load_manifest
from seqrefactor.eval.random_study import prerequisite_violation_fraction, sample_random_baseline


def test_violation_fraction_is_zero_for_a_valid_topological_order() -> None:
    g = graph_from_manifest(load_manifest("pilot_checkout_v1"))
    prereqs = [e for e in g.edges if e.polarity == "prerequisite"]
    # A valid order: every prerequisite's src before dst (topological sort by hand,
    # exploiting that s1 (GodClass) precedes everything else in this fixture).
    ids = [n.id for n in g.nodes]
    ids.sort(key=lambda sid: 0 if sid == "s1" else 1)
    assert prerequisite_violation_fraction(g, ids) == 0.0
    assert prereqs  # sanity: real prerequisites exist to have been respected


def test_violation_fraction_is_nonzero_for_a_reversed_order() -> None:
    g = graph_from_manifest(load_manifest("pilot_checkout_v1"))
    reversed_ids = [n.id for n in g.nodes][::-1]
    assert prerequisite_violation_fraction(g, reversed_ids) > 0.0


def test_sample_random_baseline_reports_real_mean_and_spread() -> None:
    g = graph_from_manifest(load_manifest("pilot_checkout_v1"))
    result = sample_random_baseline("pilot_checkout_v1", g, n_samples=50, seed=1)

    assert result.n_samples == 50
    assert 0.0 <= result.mean_violation_fraction <= 1.0
    assert result.stdev_violation_fraction >= 0.0
    assert result.seqrefactor_objective >= result.mean_random_topological_objective - 1e-9


def test_sample_random_baseline_is_deterministic_given_the_same_seed() -> None:
    g = graph_from_manifest(load_manifest("pilot_checkout_v1"))
    a = sample_random_baseline("pilot_checkout_v1", g, n_samples=30, seed=5)
    b = sample_random_baseline("pilot_checkout_v1", g, n_samples=30, seed=5)
    assert a == b
