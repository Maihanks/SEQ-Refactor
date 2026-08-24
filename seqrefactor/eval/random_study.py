"""Random-baseline reference statistics (Working Brief Phase 2c §3): "For
Random, report the mean and spread across the sampled permutations, not a
single draw."

Computed directly against a subject's real graph (no JVM/sidecar needed,
unlike the live orchestrator strategies of the same name in
``order/random_baseline.py``, which each execute exactly one seeded draw per
step as part of a real pipeline run): many independent samples per subject,
summarised by mean and standard deviation, giving the "how unsafe is an
arbitrary order, and how much does that vary" upper reference the brief asks
for.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass

from seqrefactor.model import ImpactWeights, SmellDependencyGraph
from seqrefactor.order.impact import score
from seqrefactor.order.random_baseline import random_order, random_topological_order
from seqrefactor.order.search_based import objective


@dataclass
class RandomBaselineResult:
    subject: str
    n_samples: int
    mean_violation_fraction: float
    stdev_violation_fraction: float
    mean_random_topological_objective: float
    stdev_random_topological_objective: float
    seqrefactor_objective: float  # for scale: what the greedy decoder itself achieves


def prerequisite_violation_fraction(graph: SmellDependencyGraph, agenda: list[str]) -> float:
    """Fraction of prerequisite edges an ``agenda`` places out of order (0.0
    for a fully safe agenda). The "how unsafe is this permutation" measure
    the brief's ``random`` reference is meant to characterise."""
    prerequisites = [e for e in graph.edges if e.polarity == "prerequisite"]
    if not prerequisites:
        return 0.0
    pos = {sid: i for i, sid in enumerate(agenda)}
    violations = sum(1 for e in prerequisites if pos.get(e.src, -1) > pos.get(e.dst, -2))
    return violations / len(prerequisites)


def sample_random_baseline(
    subject: str,
    graph: SmellDependencyGraph,
    n_samples: int = 200,
    seed: int = 20260101,
    discount: float = 0.9,
    weights: ImpactWeights | None = None,
) -> RandomBaselineResult:
    weights = weights or ImpactWeights()
    impact = score(graph, weights)
    rng = random.Random(f"{subject}:{seed}")

    violation_fractions: list[float] = []
    topo_objectives: list[float] = []
    for _ in range(n_samples):
        sample_seed = rng.randrange(2**32)
        random_agenda = random_order(graph, seed=sample_seed).agenda
        violation_fractions.append(prerequisite_violation_fraction(graph, random_agenda))

        topo = random_topological_order(graph, seed=sample_seed)
        topo_objectives.append(objective(topo.agenda, impact, discount))

    from seqrefactor.order.orderer import order as decode_order

    seqrefactor_objective = objective(decode_order(graph, impact).agenda, impact, discount)

    return RandomBaselineResult(
        subject=subject,
        n_samples=n_samples,
        mean_violation_fraction=round(statistics.mean(violation_fractions), 4),
        stdev_violation_fraction=round(
            statistics.stdev(violation_fractions) if n_samples > 1 else 0.0, 4
        ),
        mean_random_topological_objective=round(statistics.mean(topo_objectives), 4),
        stdev_random_topological_objective=round(
            statistics.stdev(topo_objectives) if n_samples > 1 else 0.0, 4
        ),
        seqrefactor_objective=round(seqrefactor_objective, 4),
    )


def run_study(
    entries: list[tuple[str, SmellDependencyGraph]],
    n_samples: int = 200,
    seed: int = 20260101,
) -> list[RandomBaselineResult]:
    return [sample_random_baseline(s, g, n_samples=n_samples, seed=seed) for s, g in entries]
