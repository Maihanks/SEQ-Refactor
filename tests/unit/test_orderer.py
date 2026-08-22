"""Unit tests for order/orderer.py's signed-edge tie-break, instrumentation, and
condensation memoisation (Working Brief §2 acceptance check, §3, §4).
"""

from __future__ import annotations

from seqrefactor.model import DepEdge, ImpactWeights, SmellDependencyGraph, SmellInstance
from seqrefactor.order.impact import score
from seqrefactor.order.orderer import order


def _graph(nodes: list[SmellInstance], edges: list[DepEdge]) -> SmellDependencyGraph:
    return SmellDependencyGraph(nodes=nodes, edges=edges)


def test_positive_negative_edges_never_gate_feasibility() -> None:
    """A POSITIVE or NEGATIVE edge from a to b must NOT force a to precede b --
    only PREREQUISITE edges are hard constraints (Working Brief §2 acceptance check)."""
    a = SmellInstance(id="a", category="X", loc=["A"], severity=0.1)
    b = SmellInstance(id="b", category="Y", loc=["B"], severity=1.0)  # much higher impact
    g = _graph(
        [a, b],
        [DepEdge(src="a", dst="b", provenance="test", polarity="negative", probability=0.9)],
    )
    impact = score(g, ImpactWeights())
    out = order(g, impact)

    # b has strictly higher impact and there is no PREREQUISITE edge constraining it,
    # so b must be free to be selected before a despite the soft negative edge a->b.
    assert out.agenda.index("b") < out.agenda.index("a")
    assert out.escalations == []


def test_prerequisite_edge_still_gates_feasibility_alongside_signed_edges() -> None:
    """A PREREQUISITE edge in the same graph as signed edges is still a hard
    constraint -- polarity filtering must not accidentally drop real prerequisites."""
    a = SmellInstance(id="a", category="X", loc=["A"], severity=0.1)
    b = SmellInstance(id="b", category="Y", loc=["B"], severity=1.0)
    g = _graph(
        [a, b],
        [DepEdge(src="a", dst="b", provenance="test", polarity="prerequisite")],
    )
    impact = score(g, ImpactWeights())
    out = order(g, impact)

    assert out.agenda == ["a", "b"]


def test_signed_mass_breaks_ties_among_equal_impact_smells() -> None:
    """Among smells of identical impact (both ready, no prerequisite between them),
    the one with more outstanding positive/negative mass towards an unresolved
    peer is preferred (cascade anticipation / co-resolution realisation)."""
    a = SmellInstance(id="a", category="X", loc=["A"], severity=0.5)
    b = SmellInstance(id="b", category="Y", loc=["B"], severity=0.5)
    c = SmellInstance(id="c", category="Z", loc=["C"], severity=0.5)
    g = _graph(
        [a, b, c],
        [DepEdge(src="a", dst="c", provenance="test", polarity="positive", probability=0.8)],
    )
    # a and b have identical severity/coupling/co-occurrence-degree-independent impact
    # inputs except a's extra signed edge; force equal raw impact by using a flat map.
    flat_impact = {"a": 0.5, "b": 0.5, "c": 0.5}
    out = order(g, flat_impact)

    assert out.agenda.index("a") < out.agenda.index("b")


def test_operation_counters_are_populated_and_nonzero() -> None:
    a = SmellInstance(id="a", category="X", loc=["A"])
    b = SmellInstance(id="b", category="Y", loc=["B"])
    g = _graph([a, b], [DepEdge(src="a", dst="b", provenance="test")])
    out = order(g, {"a": 1.0, "b": 1.0})

    assert out.counters.vertex_touches > 0
    assert out.counters.heap_operations > 0


def test_condensation_cache_hit_skips_renumbering_on_unchanged_residual() -> None:
    """A persisting cycle alongside a dependent singleton across two calls with an
    unchanged residual must reuse the cached condensation order (Working Brief
    §3, deliverable 4) -- the second call's renumbering counter stays at zero
    while the escalation and agenda outputs stay identical (mirrors
    notification_mixed_v1's cycle-plus-dependent structure)."""
    a = SmellInstance(id="a", category="X", loc=["A"])
    b = SmellInstance(id="b", category="Y", loc=["B"])
    c = SmellInstance(id="c", category="Z", loc=["C"])  # depends on a, a member of the cycle
    g = _graph(
        [a, b, c],
        [
            DepEdge(src="a", dst="b", provenance="cycle"),
            DepEdge(src="b", dst="a", provenance="cycle"),
            DepEdge(src="a", dst="c", provenance="dependent"),
        ],
    )
    impact = {"a": 1.0, "b": 1.0, "c": 1.0}
    cache: dict = {}
    first = order(g, impact, condensation_cache=cache)
    second = order(g, impact, condensation_cache=cache)

    assert first.escalations == [["a", "b"]]
    assert first.agenda == ["c"]
    assert second.agenda == first.agenda
    assert second.escalations == first.escalations
    assert first.counters.order_renumbering_operations == 1
    assert second.counters.order_renumbering_operations == 0
