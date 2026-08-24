"""Unit tests for order/random_baseline.py (Working Brief Phase 2c §3)."""

from __future__ import annotations

from seqrefactor.datasets import graph_from_manifest, list_subjects, load_manifest
from seqrefactor.order.random_baseline import random_order, random_topological_order


def test_random_order_is_a_permutation_of_every_vertex() -> None:
    g = graph_from_manifest(load_manifest("pilot_checkout_v1"))
    result = random_order(g, seed=1)
    assert sorted(result.agenda) == sorted(n.id for n in g.nodes)
    assert result.escalations == []


def test_random_order_is_deterministic_given_the_same_seed() -> None:
    g = graph_from_manifest(load_manifest("pilot_checkout_v1"))
    a = random_order(g, seed=7)
    b = random_order(g, seed=7)
    assert a.agenda == b.agenda


def test_random_order_can_violate_prerequisites() -> None:
    """Over many seeds, at least one draw violates the real prerequisite
    structure -- if this never happened, `random` would not be a meaningful
    "how often is an arbitrary order unsafe" reference."""
    g = graph_from_manifest(load_manifest("pilot_checkout_v1"))
    prereqs = [e for e in g.edges if e.polarity == "prerequisite"]
    assert prereqs  # sanity: this subject has real prerequisites to violate

    any_violation = False
    for seed in range(50):
        result = random_order(g, seed=seed)
        pos = {sid: i for i, sid in enumerate(result.agenda)}
        if any(pos[e.src] > pos[e.dst] for e in prereqs):
            any_violation = True
            break
    assert any_violation


def test_random_topological_order_never_violates_prerequisites() -> None:
    for subject in list_subjects():
        g = graph_from_manifest(load_manifest(subject))
        for seed in range(5):
            result = random_topological_order(g, seed=seed)
            pos = {sid: i for i, sid in enumerate(result.agenda)}
            for e in g.edges:
                if e.polarity == "prerequisite" and e.src in pos and e.dst in pos:
                    assert pos[e.src] < pos[e.dst], f"[{subject}] seed={seed} safety violated"


def test_random_topological_order_is_deterministic_given_the_same_seed() -> None:
    g = graph_from_manifest(load_manifest("pilot_checkout_v1"))
    a = random_topological_order(g, seed=3)
    b = random_topological_order(g, seed=3)
    assert a.agenda == b.agenda
    assert a.escalations == b.escalations


def test_random_topological_order_varies_across_seeds() -> None:
    """Not a smoke test of "it runs" -- confirms different seeds actually
    explore different valid orderings, not always the same one."""
    g = graph_from_manifest(load_manifest("synth_medium_medium"))
    agendas = {tuple(random_topological_order(g, seed=s).agenda) for s in range(20)}
    assert len(agendas) > 1
