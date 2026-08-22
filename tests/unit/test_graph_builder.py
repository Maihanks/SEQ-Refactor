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
    """The builder's containment-derived PREREQUISITE edges must match the
    manifest's declared prerequisites exactly. The manifest's *injected*
    positive/negative dependencies (Working Brief §7) are hand-declared ground
    truth independent of containment (see tests/support.py's docstring) and
    are deliberately excluded from this comparison -- build() has no way to
    derive them from these smells' categories/locations, by design."""
    manifest = load_manifest("pilot_checkout_v1")
    ground_truth = graph_from_manifest(manifest)
    expected_prerequisites = {
        (e.src, e.dst) for e in ground_truth.edges if e.polarity == "prerequisite"
    }

    built = build(ground_truth.nodes)
    built_pairs = {(e.src, e.dst) for e in built.edges}

    assert built_pairs == expected_prerequisites
    assert all(e.provenance for e in built.edges)


def test_all_edges_default_to_prerequisite_polarity() -> None:
    """Every edge the builder emits over the existing (prerequisite-only) catalogue
    is a hard PREREQUISITE edge unless a signed rule specifically matches."""
    manifest = load_manifest("pilot_checkout_v1")
    ground_truth = graph_from_manifest(manifest)

    built = build(ground_truth.nodes)

    assert all(e.polarity == "prerequisite" for e in built.edges)
    assert all(e.probability == 1.0 for e in built.edges)


def test_signed_rule_emits_positive_edge_with_probability_and_operation() -> None:
    # LongMethod -> FeatureEnvy is catalogue rule P1 (positive, co-resolution).
    long_method = SmellInstance(id="l1", category="LongMethod", loc=["Foo"])
    feature_envy = SmellInstance(id="f1", category="FeatureEnvy", loc=["Foo.bar"])

    graph = build([long_method, feature_envy])

    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert (edge.src, edge.dst) == ("l1", "f1")
    assert edge.polarity == "positive"
    assert edge.provenance == "signed:P1"
    assert 0.0 < edge.probability <= 1.0
    assert edge.inducing_operation == "Extract Method"


def test_signed_rule_emits_negative_edge() -> None:
    # FeatureEnvy -> ShotgunSurgery is catalogue rule N1 (negative, cascading).
    feature_envy = SmellInstance(id="f1", category="FeatureEnvy", loc=["Foo"])
    shotgun = SmellInstance(id="s1", category="ShotgunSurgery", loc=["Foo.bar"])

    graph = build([feature_envy, shotgun])

    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.polarity == "negative"
    assert edge.provenance == "signed:N1"


def test_signed_edge_takes_priority_over_structural_fallback() -> None:
    """A co-located pair matching a signed rule gets the signed (soft) edge, not
    the generic structural (hard) fallback -- signed rules are checked first."""
    long_method = SmellInstance(id="l1", category="LongMethod", loc=["Foo"])
    feature_envy = SmellInstance(id="f1", category="FeatureEnvy", loc=["Foo.bar"])

    graph = build([long_method, feature_envy])

    assert graph.edges[0].provenance != ""
    assert not graph.edges[0].provenance.startswith("structural:")
