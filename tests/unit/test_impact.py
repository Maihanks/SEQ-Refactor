"""Unit tests for impact scoring (Software Specification §9.1, Eq. 1)."""

from __future__ import annotations

from seqrefactor.model import DepEdge, ImpactWeights, SmellDependencyGraph, SmellInstance
from seqrefactor.order.impact import normalise, score


def test_normalise_maps_to_unit_interval() -> None:
    values = {"a": 1.0, "b": 5.0, "c": 3.0}
    out = normalise(values)
    assert out["a"] == 0.0
    assert out["b"] == 1.0
    assert 0.0 < out["c"] < 1.0


def test_normalise_degenerate_input_is_all_zero() -> None:
    out = normalise({"a": 4.0, "b": 4.0})
    assert out == {"a": 0.0, "b": 0.0}


def test_score_is_deterministic_and_respects_weights() -> None:
    graph = SmellDependencyGraph(
        nodes=[
            SmellInstance(id="a", category="GodClass", loc=["X"], severity=1.0),
            SmellInstance(id="b", category="LongMethod", loc=["X.m"], severity=0.2),
        ],
        edges=[DepEdge(src="a", dst="b", provenance="rule:R1")],
    )
    weights = ImpactWeights(alpha=0.0, beta=1.0, gamma=0.0)

    first = score(graph, weights)
    second = score(graph, weights)

    assert first == second
    assert first["a"] > first["b"]  # higher severity -> higher complexity contribution


def test_score_output_within_unit_interval() -> None:
    graph = SmellDependencyGraph(
        nodes=[
            SmellInstance(id="a", category="GodClass", loc=["X"], severity=0.9),
            SmellInstance(id="b", category="LongMethod", loc=["X.m"], severity=0.4),
            SmellInstance(id="c", category="FeatureEnvy", loc=["X.n"], severity=0.6),
        ],
        edges=[],
    )
    weights = ImpactWeights()

    result = score(graph, weights)

    assert all(0.0 <= v <= 1.0 for v in result.values())
