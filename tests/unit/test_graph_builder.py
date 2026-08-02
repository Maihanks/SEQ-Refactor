"""Unit tests for the graph builder (Software Specification §9.1, §5.3).

Catalogue rules and co-location must produce the expected edges with correct
provenance on hand-built fixtures, and must reproduce a synthetic subject's
ground-truth prerequisite edges from its detected smells alone (§8.1 /
Task 4 "done when").
"""

from __future__ import annotations

from seqrefactor.graph.builder import build
from seqrefactor.model import SmellInstance
from tests.support import graph_from_manifest, load_manifest


def test_catalogue_rule_edge_has_rule_provenance() -> None:
    god_class = SmellInstance(id="g1", category="GodClass", loc=["Foo"])
    feature_envy = SmellInstance(id="f1", category="FeatureEnvy", loc=["Foo.bar"])

    graph = build([god_class, feature_envy])

    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert (edge.src, edge.dst) == ("g1", "f1")
    assert edge.provenance == "rule:R1"


def test_structural_coloc_edge_used_when_no_catalogue_rule_matches() -> None:
    god_class = SmellInstance(id="g1", category="GodClass", loc=["Foo"])
    long_method = SmellInstance(id="l1", category="LongMethod", loc=["Foo.checkout"])

    graph = build([god_class, long_method])

    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert (edge.src, edge.dst) == ("g1", "l1")
    assert edge.provenance.startswith("structural:")


def test_sibling_elements_produce_no_spurious_edge() -> None:
    a = SmellInstance(id="a", category="LongMethod", loc=["Foo.bar"])
    b = SmellInstance(id="b", category="LongMethod", loc=["Foo.baz"])

    graph = build([a, b])

    assert graph.edges == []


def test_builder_reproduces_pilot_manifest_ground_truth_edges() -> None:
    manifest = load_manifest("pilot_checkout_v1")
    ground_truth = graph_from_manifest(manifest)

    built = build(ground_truth.nodes)
    built_pairs = {(e.src, e.dst) for e in built.edges}
    expected_pairs = {(e.src, e.dst) for e in ground_truth.edges}

    assert built_pairs == expected_pairs
    assert all(e.provenance for e in built.edges)
