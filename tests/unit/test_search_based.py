"""Unit tests for order/search_based.py (Working Brief, Phase 2, §4)."""

from __future__ import annotations

from seqrefactor.datasets import graph_from_manifest, list_subjects, load_manifest
from seqrefactor.model import ImpactWeights
from seqrefactor.order.impact import score
from seqrefactor.order.orderer import order
from seqrefactor.order.search_based import objective, search_based_order


def _graph_and_impact(subject: str):
    manifest = load_manifest(subject)
    g = graph_from_manifest(manifest)
    return g, score(g, ImpactWeights())


def test_search_based_never_violates_prerequisites() -> None:
    for subject in list_subjects():
        g, impact = _graph_and_impact(subject)
        result = search_based_order(g, impact, seed=1, population_size=10, generations=10)
        pos = {sid: i for i, sid in enumerate(result.agenda)}
        for e in g.edges:
            if e.polarity == "prerequisite" and e.src in pos and e.dst in pos:
                assert pos[e.src] < pos[e.dst], f"[{subject}] safety violated by search_based"


def test_search_based_escalations_match_the_safe_decoder() -> None:
    """Safety is never searched away: escalations come from the same decoder
    (order/orderer.order) every other strategy uses."""
    for subject in list_subjects():
        g, impact = _graph_and_impact(subject)
        baseline = order(g, impact)
        result = search_based_order(g, impact, seed=1, population_size=10, generations=10)
        # The search's escalation set is whatever ITS best individual's decode produced;
        # since escalation only depends on the PREREQUISITE subgraph (never on priority),
        # it must match the plain decoder's escalations regardless of which individual won.
        assert result.escalations == baseline.escalations, subject


def test_search_based_objective_stays_close_to_greedy() -> None:
    """Not "always >= greedy": empirically (see PHASE2_PLAN.md / CORPUS.md write-up),
    the GA matches greedy exactly on smaller/forest-shaped subjects but can fall
    marginally short (observed: within ~1% relative) on the largest graphs within a
    bounded population/generation budget -- a real, honest finding, not something to
    tune away. This test only guards against a gross regression (e.g. a decode bug
    that made search essentially random), not against that expected small gap."""
    for subject in list_subjects():
        g, impact = _graph_and_impact(subject)
        greedy = order(g, impact)
        result = search_based_order(g, impact, discount=0.9, seed=3)  # module defaults

        j_greedy = objective(greedy.agenda, impact, 0.9)
        j_search = objective(result.agenda, impact, 0.9)
        if j_greedy <= 0:
            continue  # empty/degenerate agenda (e.g. fully-cyclic subject): nothing to compare
        relative_gap = (j_search - j_greedy) / j_greedy
        assert relative_gap >= -0.05, f"[{subject}] search fell {-relative_gap:.1%} short of greedy"


def test_search_based_is_deterministic_given_the_same_seed() -> None:
    g, impact = _graph_and_impact("pilot_checkout_v1")
    a = search_based_order(g, impact, seed=5, population_size=10, generations=10)
    b = search_based_order(g, impact, seed=5, population_size=10, generations=10)
    assert a.agenda == b.agenda
    assert a.escalations == b.escalations


def test_search_based_falls_back_cleanly_below_two_nodes() -> None:
    g, _impact = _graph_and_impact("pilot_checkout_v1")
    single = g.__class__(nodes=g.nodes[:1], edges=[])
    result = search_based_order(single, {g.nodes[0].id: 1.0}, seed=1)
    assert result.agenda == [g.nodes[0].id]
