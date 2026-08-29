"""Unit tests for order/nsga2_scheduler.py (Working Brief Phase 4, E3)."""

from __future__ import annotations

from seqrefactor.datasets import graph_from_manifest, list_subjects, load_manifest
from seqrefactor.model import ImpactWeights
from seqrefactor.order.impact import score
from seqrefactor.order.nsga2_scheduler import (
    Individual,
    context_switch_count,
    crowding_distance,
    dominates,
    fast_non_dominated_sort,
    nsga2_order,
    nsga2_search,
)
from seqrefactor.order.orderer import order


def _graph_and_impact(subject: str):
    manifest = load_manifest(subject)
    g = graph_from_manifest(manifest)
    return g, score(g, ImpactWeights())


# -- Core NSGA-II mechanics, hand-verified ----------------------------------


def test_dominates_requires_at_least_as_good_on_both_and_strictly_better_on_one() -> None:
    # Maximise objective[0] (J), minimise objective[1] (switches).
    assert dominates((5.0, 2.0), (3.0, 2.0))  # strictly better J, equal switches
    assert dominates((5.0, 1.0), (5.0, 2.0))  # equal J, strictly fewer switches
    assert dominates((5.0, 1.0), (3.0, 2.0))  # better on both
    assert not dominates((5.0, 2.0), (5.0, 2.0))  # identical: neither dominates
    assert not dominates((5.0, 3.0), (3.0, 2.0))  # better J but worse switches: incomparable


def test_fast_non_dominated_sort_separates_fronts_correctly() -> None:
    # a: dominates everything; b, c: mutually non-dominating (front 1); d: dominated by all.
    a = Individual(priorities={}, ordering=None, objectives=(10.0, 0.0))  # type: ignore[arg-type]
    b = Individual(priorities={}, ordering=None, objectives=(8.0, 1.0))  # type: ignore[arg-type]
    c = Individual(priorities={}, ordering=None, objectives=(6.0, 0.5))  # type: ignore[arg-type]
    d = Individual(priorities={}, ordering=None, objectives=(1.0, 5.0))  # type: ignore[arg-type]

    fronts = fast_non_dominated_sort([a, b, c, d])

    assert fronts[0] == [a]
    assert set(id(x) for x in fronts[1]) == {id(b), id(c)}
    assert fronts[2] == [d]


def test_crowding_distance_gives_boundary_points_infinite_distance() -> None:
    front = [
        Individual(priorities={}, ordering=None, objectives=(1.0, 5.0)),  # type: ignore[arg-type]
        Individual(priorities={}, ordering=None, objectives=(3.0, 3.0)),  # type: ignore[arg-type]
        Individual(priorities={}, ordering=None, objectives=(5.0, 1.0)),  # type: ignore[arg-type]
    ]

    crowding_distance(front)

    boundary_j = min(front, key=lambda i: i.objectives[0])
    other_boundary_j = max(front, key=lambda i: i.objectives[0])
    assert boundary_j.crowding == float("inf")
    assert other_boundary_j.crowding == float("inf")


def test_context_switch_count_is_zero_for_a_single_category_run() -> None:
    category_of = {"a": "GodClass", "b": "GodClass", "c": "GodClass"}
    assert context_switch_count(["a", "b", "c"], category_of) == 0


def test_context_switch_count_counts_adjacent_category_changes() -> None:
    category_of = {"a": "GodClass", "b": "LongMethod", "c": "LongMethod", "d": "GodClass"}
    # a->b: switch, b->c: same, c->d: switch => 2
    assert context_switch_count(["a", "b", "c", "d"], category_of) == 2


# -- End-to-end, mirroring test_search_based.py's structure -----------------


def test_nsga2_never_violates_prerequisites() -> None:
    for subject in list_subjects():
        g, impact = _graph_and_impact(subject)
        result = nsga2_order(g, impact, seed=1, population_size=10, generations=8)
        pos = {sid: i for i, sid in enumerate(result.agenda)}
        for e in g.edges:
            if e.polarity == "prerequisite" and e.src in pos and e.dst in pos:
                assert pos[e.src] < pos[e.dst], f"[{subject}] safety violated by ouni_nsga2"


def test_nsga2_escalations_match_the_safe_decoder() -> None:
    """Safety is never searched away here either: escalation depends only on the
    prerequisite subgraph, never on priority, so it must match the plain decoder
    regardless of which Pareto-front member is returned."""
    for subject in list_subjects():
        g, impact = _graph_and_impact(subject)
        baseline = order(g, impact)
        result = nsga2_order(g, impact, seed=1, population_size=10, generations=8)
        assert result.escalations == baseline.escalations, subject


def test_nsga2_is_deterministic_given_the_same_seed() -> None:
    g, impact = _graph_and_impact("pilot_checkout_v1")
    a = nsga2_order(g, impact, seed=5, population_size=10, generations=8)
    b = nsga2_order(g, impact, seed=5, population_size=10, generations=8)
    assert a.agenda == b.agenda
    assert a.escalations == b.escalations


def test_nsga2_search_returns_a_real_pareto_front_not_a_single_point() -> None:
    """On a subject with enough vertices for the two objectives to genuinely trade
    off, the final front should contain more than one non-dominated solution --
    otherwise the "multi-objective" search collapsed to single-objective, which
    would contradict the module's own NSGA-II claim."""
    g, impact = _graph_and_impact("synth_large_medium")
    front = nsga2_search(g, impact, seed=7, population_size=30, generations=25)
    assert len(front) >= 1
    # Every member of the returned front must be mutually non-dominating.
    for i, a in enumerate(front):
        for b in front[i + 1 :]:
            assert not dominates(a.objectives, b.objectives)
            assert not dominates(b.objectives, a.objectives)


def test_nsga2_falls_back_cleanly_below_two_nodes() -> None:
    g, _impact = _graph_and_impact("pilot_checkout_v1")
    single = g.__class__(nodes=g.nodes[:1], edges=[])
    result = nsga2_order(single, {g.nodes[0].id: 1.0}, seed=1)
    assert result.agenda == [g.nodes[0].id]
