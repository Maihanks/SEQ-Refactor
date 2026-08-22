"""The bit-for-bit equivalence gate for H5 (Working Brief §3, "Acceptance check
(this is the gate for H5)"): the incrementally-maintained graph and order must
be identical to a from-scratch rebuild, on every step, or it's a bug.

Two complementary checks:

1. Property-based (Hypothesis): random smell "forests" (classes with 0-3
   contained methods, each a random category, so both catalogue-rule and
   structural-fallback edges get exercised) with a random resolved node and a
   random freshly-rescanned replacement set. This is deliberately expressed
   over the smell/category/containment domain graph.builder actually consumes
   (not raw arbitrary DAG edges), since that is apply_step's real input
   surface -- a raw-edge-list fuzzer would not exercise the catalogue/signed/
   structural-fallback edge derivation this module's correctness depends on.
2. Per-subject, per-step (over the whole synthetic corpus, brief's literal
   "run this over the whole subject corpus"): starting from each manifest's
   ground-truth graph, repeatedly resolve the from-scratch agenda's next item
   via apply_step and cross-check against an independent from-scratch rebuild,
   continuing on the incrementally-maintained graph so errors compound across
   steps rather than being reset every time.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from seqrefactor.graph.builder import build
from seqrefactor.graph.incremental import apply_step, touched_node_ids
from seqrefactor.model import ImpactWeights, OperationCounters, SmellInstance
from seqrefactor.order.impact import score
from seqrefactor.order.orderer import order
from tests.support import graph_from_manifest, list_subjects, load_manifest

CATEGORIES = [
    "GodClass",
    "LongMethod",
    "FeatureEnvy",
    "DuplicatedCode",
    "LargeClass",
    "DivergentChange",
    "ShotgunSurgery",
    "MessageChains",
    "MiddleMan",
    "BigSwitch",
    "Uncatalogued",  # exercises the structural-fallback path (no rule of either kind)
]


@st.composite
def smell_forest(draw: st.DrawFn) -> list[SmellInstance]:
    n_classes = draw(st.integers(min_value=1, max_value=4))
    nodes: list[SmellInstance] = []
    counter = 0
    for c in range(n_classes):
        class_name = f"C{c}"
        counter += 1
        nodes.append(
            SmellInstance(id=f"n{counter}", category=draw(st.sampled_from(CATEGORIES)), loc=[class_name])
        )
        for m in range(draw(st.integers(min_value=0, max_value=3))):
            counter += 1
            nodes.append(
                SmellInstance(
                    id=f"n{counter}",
                    category=draw(st.sampled_from(CATEGORIES)),
                    loc=[f"{class_name}.m{m}"],
                )
            )
    return nodes


def _edge_signature(graph):
    return {(e.src, e.dst, e.polarity, e.probability, e.provenance) for e in graph.edges}


@settings(max_examples=150, deadline=None)
@given(nodes=smell_forest(), data=st.data())
def test_incremental_equals_from_scratch_on_random_forests(nodes, data) -> None:
    graph = build(nodes)
    resolved = data.draw(st.sampled_from(nodes))
    touched = {resolved.loc[0]}

    rescanned: list[SmellInstance] = []
    for i in range(data.draw(st.integers(min_value=0, max_value=2))):
        rescanned.append(
            SmellInstance(
                id=f"new{i}_{resolved.id}",
                category=data.draw(st.sampled_from(CATEGORIES)),
                loc=[resolved.loc[0]],
            )
        )

    counters = OperationCounters()
    incremental_graph = apply_step(graph, resolved.id, rescanned, touched, counters)

    stale = touched_node_ids(graph.nodes, touched) | {resolved.id}
    survivors = [n for n in graph.nodes if n.id not in stale]
    from_scratch_graph = build(survivors + rescanned)

    assert incremental_graph.node_ids() == from_scratch_graph.node_ids()
    assert _edge_signature(incremental_graph) == _edge_signature(from_scratch_graph)

    weights = ImpactWeights()
    out_incremental = order(incremental_graph, score(incremental_graph, weights))
    out_scratch = order(from_scratch_graph, score(from_scratch_graph, weights))
    assert out_incremental.agenda == out_scratch.agenda
    assert out_incremental.escalations == out_scratch.escalations


def _step_and_cross_check(graph, weights: ImpactWeights) -> tuple[object, bool]:
    """Resolve the from-scratch agenda's next item via apply_step, cross-check
    against an independent from-scratch rebuild, return (next_graph, continued).

    The manifests' ground-truth edges (tests/support.py's graph_from_manifest)
    are hand-authored, not derivable from graph_builder.build's containment
    heuristics -- notification_mixed_v1 and billing_cycle_v1 declare cycles
    between structurally-sibling elements on purpose (to exercise SCC
    escalation), which build() would never produce from containment alone. So
    the correct "from-scratch" oracle for a manifest-driven graph is the
    manifest's own edges restricted to survivors, exactly what apply_step's
    kept_edges is supposed to compute -- not a re-derivation via build().
    """
    out_scratch = order(graph, score(graph, weights))
    if not out_scratch.agenda:
        return graph, False  # nothing left safely resolvable (empty, or pure cycle residual)

    resolved_id = out_scratch.agenda[0]
    resolved_node = next(n for n in graph.nodes if n.id == resolved_id)
    touched = set(resolved_node.loc)

    incremental_graph = apply_step(graph, resolved_id, rescanned_smells=[], touched_elements=touched)

    stale = touched_node_ids(graph.nodes, touched) | {resolved_id}
    survivors = [n for n in graph.nodes if n.id not in stale]
    survivor_ids = {n.id for n in survivors}
    from_scratch_graph = graph.__class__(
        nodes=survivors,
        edges=[e for e in graph.edges if e.src in survivor_ids and e.dst in survivor_ids],
    )

    assert incremental_graph.node_ids() == from_scratch_graph.node_ids()
    assert _edge_signature(incremental_graph) == _edge_signature(from_scratch_graph)

    out_incremental = order(incremental_graph, score(incremental_graph, weights))
    out_scratch_next = order(from_scratch_graph, score(from_scratch_graph, weights))
    assert out_incremental.agenda == out_scratch_next.agenda
    assert out_incremental.escalations == out_scratch_next.escalations

    return incremental_graph, True


def test_equivalence_holds_at_every_step_across_the_whole_synthetic_corpus() -> None:
    weights = ImpactWeights()
    for subject in list_subjects():
        manifest = load_manifest(subject)
        graph = graph_from_manifest(manifest)

        steps = 0
        cont = True
        while cont and steps < 50:  # generous bound; real subjects resolve in <10 steps
            graph, cont = _step_and_cross_check(graph, weights)
            steps += 1

        assert steps < 50, f"[{subject}] equivalence loop did not terminate within bound"
