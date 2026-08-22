"""Unit tests for graph/incremental.py's scoped update (Working Brief §3).

Focused, hand-built-fixture tests; the bit-for-bit equivalence proof against
the from-scratch baseline lives in tests/property/test_incremental_equivalence.py.
"""

from __future__ import annotations

from seqrefactor.graph.builder import build
from seqrefactor.graph.incremental import apply_step, touched_node_ids
from seqrefactor.model import OperationCounters, SmellInstance


def test_touched_node_ids_matches_class_and_method_level_smells() -> None:
    god = SmellInstance(id="g1", category="GodClass", loc=["Foo"])
    method = SmellInstance(id="m1", category="LongMethod", loc=["Foo.bar"])
    unrelated = SmellInstance(id="u1", category="LongMethod", loc=["Other.baz"])

    touched = touched_node_ids([god, method, unrelated], {"Foo"})

    assert touched == {"g1", "m1"}


def test_apply_step_removes_resolved_vertex_and_incident_edges() -> None:
    god = SmellInstance(id="g1", category="GodClass", loc=["Foo"])
    method = SmellInstance(id="m1", category="LongMethod", loc=["Foo.bar"])
    other = SmellInstance(id="o1", category="LongMethod", loc=["Other.baz"])
    graph = build([god, method, other])
    assert {e.dst for e in graph.edges} == {"m1"}  # sanity: god -> method edge exists

    updated = apply_step(
        graph, resolved_id="g1", rescanned_smells=[], touched_elements={"Foo"}
    )

    assert updated.node_ids() == {"o1"}  # g1 resolved, m1 was localised in the touched region
    assert updated.edges == []


def test_apply_step_merges_rescanned_smells_and_rebuilds_only_touched_edges() -> None:
    god = SmellInstance(id="g1", category="GodClass", loc=["Foo"])
    method = SmellInstance(id="m1", category="LongMethod", loc=["Foo.bar"])
    other = SmellInstance(id="o1", category="LongMethod", loc=["Other.baz"])
    graph = build([god, method, other])

    # Simulate: g1 resolved (God Class split); re-detection over the disturbed
    # region ("Foo") finds a residual FeatureEnvy where the old LongMethod was.
    envy = SmellInstance(id="e1", category="FeatureEnvy", loc=["Foo.bar"])
    updated = apply_step(
        graph,
        resolved_id="g1",
        rescanned_smells=[envy],
        touched_elements={"Foo"},
    )

    assert updated.node_ids() == {"o1", "e1"}
    # o1 is untouched: its (absence of) edges to anything is unchanged, no new edge
    # to e1 should appear since o1 and e1 are not co-located.
    assert updated.edges == []


def test_apply_step_produces_same_graph_as_full_rebuild() -> None:
    """The core equivalence property, checked directly on a hand-built case:
    scoped incremental update == graph.builder.build over the same final
    pending-smell set."""
    god = SmellInstance(id="g1", category="GodClass", loc=["Foo"])
    envy_old = SmellInstance(id="fe1", category="FeatureEnvy", loc=["Foo.old"])
    other = SmellInstance(id="o1", category="LongMethod", loc=["Other.baz"])
    graph = build([god, envy_old, other])

    envy_new = SmellInstance(id="fe2", category="FeatureEnvy", loc=["Foo.newshape"])
    incremental = apply_step(
        graph, resolved_id="g1", rescanned_smells=[envy_new], touched_elements={"Foo"}
    )

    from_scratch = build([envy_new, other])  # what full re-detection+rebuild would see

    assert incremental.node_ids() == from_scratch.node_ids()
    assert {(e.src, e.dst, e.polarity, e.provenance) for e in incremental.edges} == {
        (e.src, e.dst, e.polarity, e.provenance) for e in from_scratch.edges
    }


def test_apply_step_updates_counters() -> None:
    god = SmellInstance(id="g1", category="GodClass", loc=["Foo"])
    other = SmellInstance(id="o1", category="LongMethod", loc=["Other.baz"])
    graph = build([god, other])

    counters = OperationCounters()
    apply_step(graph, resolved_id="g1", rescanned_smells=[], touched_elements={"Foo"}, counters=counters)

    assert counters.vertex_touches > 0
