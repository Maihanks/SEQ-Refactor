"""Search-based ordering (Working Brief, Phase 2, Section 4): a genetic-algorithm
search for a high-J(pi) valid linear extension, the discounted cumulative-impact
objective (paper Eq. 2-3) that Algorithm 1 (``order/orderer.py``) only greedily
approximates ("We do not claim to solve (3) optimally... a greedy choice can
forgo a higher discounted return", Algorithm 1's own Correctness discussion).
Positioned as a fifth strategy arm to answer the reviewer question the brief
names directly: how much value does greedy priority selection leave on the
table versus actually searching for it?

HONESTY NOTE: in the spirit of the search-based refactoring-scheduling
literature already cited in the paper (Ouni et al. [29], a multi-objective
search over refactoring sequences; Liu et al. [30], scheduling bad-smell
resolution), this is a real, working genetic algorithm, not a verified
reproduction of either paper's exact formulation -- this environment cannot
fetch either paper to check what is implemented here against their published
pseudocode byte-for-byte, and claiming that fidelity without being able to
verify it would be exactly the kind of overclaim this repository's standing
constraints rule out. What follows is real and independently verifiable by
reading it: population-based search over a priority-vector encoding, whose
decoder (``order/orderer.order``) guarantees every individual decodes to a
valid linear extension by construction -- safety is never searched away, the
same invariant every other strategy in this repository respects -- plus
tournament selection, uniform crossover, Gaussian mutation, and elitism, all
seeded for determinism (NFR-2).
"""

from __future__ import annotations

import random

from seqrefactor.model import Ordering, SmellDependencyGraph, SmellId
from seqrefactor.order.orderer import order as decode_order

DEFAULT_POPULATION_SIZE = 24
DEFAULT_GENERATIONS = 40


def objective(agenda: list[SmellId], impact: dict[SmellId, float], discount: float) -> float:
    """J(pi) = sum_i discount^(i-1) * Impact(pi_i), paper Eq. 2 (0-indexed here)."""
    return sum((discount**i) * impact.get(sid, 0.0) for i, sid in enumerate(agenda))


def search_based_order(
    graph: SmellDependencyGraph,
    impact: dict[SmellId, float],
    discount: float = 0.9,
    population_size: int = DEFAULT_POPULATION_SIZE,
    generations: int = DEFAULT_GENERATIONS,
    seed: int = 20260101,
) -> Ordering:
    """Search over per-vertex priority vectors, each decoded into a guaranteed-
    valid linear extension via the existing priority-queue-Kahn traversal
    (``order/orderer.order``), maximising ``objective`` above. Escalations
    (genuine cycles) are inherited from the decoder unchanged -- the search
    only ever chooses among safe orderings, never whether to escalate.
    """
    node_ids = [n.id for n in graph.nodes]
    if len(node_ids) < 2:
        return decode_order(graph, impact)

    rng = random.Random(seed)

    def random_individual() -> dict[SmellId, float]:
        return {sid: rng.random() for sid in node_ids}

    def fitness(individual: dict[SmellId, float]) -> tuple[float, Ordering]:
        decoded = decode_order(graph, individual)
        return objective(decoded.agenda, impact, discount), decoded

    def crossover(a: dict[SmellId, float], b: dict[SmellId, float]) -> dict[SmellId, float]:
        return {sid: (a[sid] if rng.random() < 0.5 else b[sid]) for sid in node_ids}

    def mutate(individual: dict[SmellId, float], rate: float = 0.2) -> dict[SmellId, float]:
        return {
            sid: (min(1.0, max(0.0, v + rng.gauss(0.0, 0.15))) if rng.random() < rate else v)
            for sid, v in individual.items()
        }

    def tournament(scored: list[tuple[float, dict[SmellId, float]]], k: int = 3) -> dict[SmellId, float]:
        contenders = rng.sample(scored, min(k, len(scored)))
        return max(contenders, key=lambda pair: pair[0])[1]

    population = [random_individual() for _ in range(population_size)]
    best_score = float("-inf")
    best_ordering: Ordering | None = None

    for _ in range(generations):
        scored: list[tuple[float, dict[SmellId, float]]] = []
        for individual in population:
            score, decoded = fitness(individual)
            scored.append((score, individual))
            if score > best_score:
                best_score = score
                best_ordering = decoded

        elite = max(scored, key=lambda pair: pair[0])[1]
        next_population = [elite]
        while len(next_population) < population_size:
            parent_a = tournament(scored)
            parent_b = tournament(scored)
            next_population.append(mutate(crossover(parent_a, parent_b)))
        population = next_population

    assert best_ordering is not None  # population_size >= 1 guarantees at least one score
    return best_ordering
