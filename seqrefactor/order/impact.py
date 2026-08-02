"""Impact scoring (Software Specification §7.2, paper Eq. 1).

``Impact(v) = alpha * coupling_hat(v) + beta * complexity_hat(v) + gamma * cooccurrence_hat(v)``,
each term normalised to [0, 1] across the module before weighting.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from seqrefactor.model import ImpactWeights, LocSet, SmellDependencyGraph, SmellId


@runtime_checkable
class MetricProvider(Protocol):
    """Supplies per-smell coupling and complexity readings from the metric facade."""

    def coupling(self, loc: LocSet) -> float: ...

    def complexity(self, loc: LocSet) -> float: ...


class SeverityMetricProvider:
    """Deterministic fallback metric provider driven only by declared severity and loc breadth.

    The ordering algorithm and its correctness (OR-1..OR-3) must be verifiable without a
    Java toolchain, so this provider needs no compiled source: coupling is approximated by
    the number of localised elements and complexity by declared severity. Real experiment
    runs should inject a facade-backed provider (seqrefactor.verify.metrics) instead.
    """

    def coupling(self, loc: LocSet) -> float:
        return float(len(loc))

    def complexity(self, loc: LocSet) -> float:
        return 1.0


def normalise(values: dict[SmellId, float]) -> dict[SmellId, float]:
    """Min-max normalise to [0, 1]; a degenerate (constant) input maps to all zeros."""
    if not values:
        return {}
    lo, hi = min(values.values()), max(values.values())
    if hi - lo < 1e-12:
        return dict.fromkeys(values, 0.0)
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}


def cooccurrence_degree(graph: SmellDependencyGraph) -> dict[SmellId, int]:
    """Number of dependency-graph interactions (in- or out-edges) each smell participates in."""
    degree: dict[SmellId, int] = {n.id: 0 for n in graph.nodes}
    for edge in graph.edges:
        degree[edge.src] = degree.get(edge.src, 0) + 1
        degree[edge.dst] = degree.get(edge.dst, 0) + 1
    return degree


def score(
    graph: SmellDependencyGraph,
    weights: ImpactWeights,
    metrics: MetricProvider | None = None,
) -> dict[SmellId, float]:
    """Compute the normalised impact score of every node in ``graph`` (Eq. 1)."""
    metrics = metrics or SeverityMetricProvider()

    coupling_raw = {n.id: metrics.coupling(n.loc) for n in graph.nodes}
    complexity_raw = {n.id: metrics.complexity(n.loc) * n.severity for n in graph.nodes}
    cooccurrence_raw = {k: float(v) for k, v in cooccurrence_degree(graph).items()}

    coupling = normalise(coupling_raw)
    complexity = normalise(complexity_raw)
    cooccurrence = normalise(cooccurrence_raw)

    return {
        n.id: (
            weights.alpha * coupling[n.id]
            + weights.beta * complexity[n.id]
            + weights.gamma * cooccurrence[n.id]
        )
        for n in graph.nodes
    }
