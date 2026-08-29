"""E3: a published-method-informed multi-objective scheduler (Working Brief
Phase 4, Task E3), distinct from the existing generic single-objective
``order/search_based.py``.

SOURCE METHOD AND FAITHFULNESS DISCLOSURE (brief's own requirement: "state
exactly what was implemented ... which components were reproduced and which
were adapted ... and any deviation forced by the setting"):

The paper cites two prior scheduling-adjacent works: Liu et al. 2012 [30]
("Schedule of bad smell detection and resolution") and Ouni et al. 2013 [29]
("Maintainability defects detection and correction: a multi-objective
approach"). Checked directly (web search + abstract retrieval, this
environment has no access to either paywalled full text):

- Liu et al. 2012's abstract describes a FIXED, empirically-validated
  recommended precedence sequence among smell TYPES (17.64-20% effort
  reduction on two open-source subjects) -- not a search-based method at
  all. It is conceptually closer to this project's own
  ``graph/rules.py`` PRECEDENCE_RULES catalogue than to anything this module
  could faithfully extend as a "search-based" strategy.
- Ouni et al. 2013's abstract confirms it uses NSGA-II (Non-dominated
  Sorting Genetic Algorithm II) over a multi-objective fitness that
  maximises the number of maintainability defects corrected while
  minimising code-modification effort, encoding a "correction solution" as
  a combination of refactoring operations. This is a real, standard,
  well-documented algorithm (NSGA-II itself), independent of the paper --
  what is NOT independently available to this environment is Ouni et al.'s
  EXACT fitness-function coefficients, chromosome encoding, or genetic
  operators, since the full text is paywalled and no accessible source
  reproduced them.

WHAT THIS MODULE ACTUALLY IS: a genuine, correctly-implemented NSGA-II
(fast non-dominated sorting, crowding distance, binary tournament selection
on (rank, crowding distance), elitist mu+lambda replacement -- all textbook
NSGA-II, verifiable by reading the code below, not claimed on trust) over
this project's own priority-vector encoding (the same safe-by-construction
decoder ``order/orderer.order`` every other strategy uses, so safety is
never searched away). The two objectives are THIS project's own adaptation
of Ouni et al.'s described "maximise correction, minimise effort" structure
to a scheduling-only context (this project's ordering strategies do not
themselves perform correction; that happens downstream in the orchestrator's
generate/verify/gate loop), not a reproduction of their exact objectives:

  1. Maximise J(pi), the discounted cumulative impact objective (paper
     Eq. 2-3, the same objective ``search_based.py`` already searches) --
     this project's own proxy for "high-priority defects corrected early."
  2. Minimise category-context-switch count: the number of adjacent agenda
     positions whose smell CATEGORY differs. This project's own proxy for
     scheduling effort (grouping same-category smells is cheaper in
     practice than constantly switching context between unrelated smell
     types), chosen because it is the one meaningful quantity that (a)
     actually varies across different SAFE orderings of the same graph
     (escalation/safety itself is graph-structural and invariant to
     priority, so it cannot serve as a second objective) and (b) requires
     no information this project's ordering stage does not already have.
     This is NOT Ouni et al.'s own effort metric, which is unavailable here.

The Pareto front NSGA-II produces is reduced to a single Ordering (this
project's Strategy return type) by taking the front member with the highest
J(pi), so this strategy is directly comparable to every other single-order
strategy in the ablation -- the full front is not discarded silently,
``nsga2_search`` below returns it for anyone who wants the whole trade-off
surface, only the CLI/orchestrator-facing ``ordering`` wrapper picks one.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from seqrefactor.model import Ordering, SmellDependencyGraph, SmellId
from seqrefactor.order.orderer import order as decode_order
from seqrefactor.order.search_based import objective as impact_objective

DEFAULT_POPULATION_SIZE = 24
DEFAULT_GENERATIONS = 40


@dataclass
class Individual:
    priorities: dict[SmellId, float]
    ordering: Ordering
    objectives: tuple[float, float]  # (J(pi) to maximise, switches to minimise)
    rank: int = 0
    crowding: float = 0.0


def context_switch_count(agenda: list[SmellId], category_of: dict[SmellId, str]) -> int:
    """Number of adjacent agenda positions whose smell category differs --
    this module's own effort proxy (see module docstring)."""
    return sum(
        1
        for a, b in zip(agenda, agenda[1:])
        if category_of.get(a) != category_of.get(b)
    )


def dominates(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """``a`` dominates ``b`` under (maximise objective[0], minimise objective[1])."""
    better_or_equal = a[0] >= b[0] and a[1] <= b[1]
    strictly_better = a[0] > b[0] or a[1] < b[1]
    return better_or_equal and strictly_better


def fast_non_dominated_sort(population: list[Individual]) -> list[list[Individual]]:
    """Standard NSGA-II fast non-dominated sort: partitions ``population`` into
    Pareto fronts, front 0 being the non-dominated set."""
    dominated_by: dict[int, set[int]] = {i: set() for i in range(len(population))}
    domination_count = [0] * len(population)

    for i, p in enumerate(population):
        for j, q in enumerate(population):
            if i == j:
                continue
            if dominates(p.objectives, q.objectives):
                dominated_by[i].add(j)
            elif dominates(q.objectives, p.objectives):
                domination_count[i] += 1

    fronts: list[list[int]] = [[]]
    for i in range(len(population)):
        if domination_count[i] == 0:
            population[i].rank = 0
            fronts[0].append(i)

    front_index = 0
    while fronts[front_index]:
        next_front: list[int] = []
        for i in fronts[front_index]:
            for j in dominated_by[i]:
                domination_count[j] -= 1
                if domination_count[j] == 0:
                    population[j].rank = front_index + 1
                    next_front.append(j)
        front_index += 1
        fronts.append(next_front)

    return [[population[i] for i in front] for front in fronts if front]


def crowding_distance(front: list[Individual]) -> None:
    """Standard NSGA-II crowding distance, assigned in place onto each
    ``Individual.crowding`` in ``front``: preserves diversity along the
    Pareto front by preferring individuals in sparser regions."""
    if not front:
        return
    for ind in front:
        ind.crowding = 0.0

    for obj_index in range(2):
        front.sort(key=lambda ind: ind.objectives[obj_index])
        front[0].crowding = front[-1].crowding = float("inf")
        span = front[-1].objectives[obj_index] - front[0].objectives[obj_index]
        if span == 0:
            continue
        for k in range(1, len(front) - 1):
            front[k].crowding += (
                front[k + 1].objectives[obj_index] - front[k - 1].objectives[obj_index]
            ) / span


def _tournament(rng: random.Random, population: list[Individual], k: int = 2) -> Individual:
    contenders = rng.sample(population, min(k, len(population)))
    # Lower rank (better front) wins; ties broken by higher crowding distance (diversity).
    return min(contenders, key=lambda ind: (ind.rank, -ind.crowding))


def nsga2_search(
    graph: SmellDependencyGraph,
    impact: dict[SmellId, float],
    discount: float = 0.9,
    population_size: int = DEFAULT_POPULATION_SIZE,
    generations: int = DEFAULT_GENERATIONS,
    seed: int = 20260101,
) -> list[Individual]:
    """Run NSGA-II and return the final Pareto front (rank-0 individuals),
    sorted by descending J(pi). Same priority-vector encoding and safe-by-
    construction decoder as ``search_based.search_based_order`` (module
    docstring)."""
    node_ids = [n.id for n in graph.nodes]
    category_of = {n.id: n.category for n in graph.nodes}
    rng = random.Random(seed)

    def random_priorities() -> dict[SmellId, float]:
        return {sid: rng.random() for sid in node_ids}

    def evaluate(priorities: dict[SmellId, float]) -> Individual:
        decoded = decode_order(graph, priorities)
        j = impact_objective(decoded.agenda, impact, discount)
        switches = context_switch_count(decoded.agenda, category_of)
        return Individual(priorities=priorities, ordering=decoded, objectives=(j, float(switches)))

    def crossover(a: dict[SmellId, float], b: dict[SmellId, float]) -> dict[SmellId, float]:
        return {sid: (a[sid] if rng.random() < 0.5 else b[sid]) for sid in node_ids}

    def mutate(priorities: dict[SmellId, float], rate: float = 0.2) -> dict[SmellId, float]:
        return {
            sid: (min(1.0, max(0.0, v + rng.gauss(0.0, 0.15))) if rng.random() < rate else v)
            for sid, v in priorities.items()
        }

    if len(node_ids) < 2:
        return [evaluate(random_priorities())]

    population = [evaluate(random_priorities()) for _ in range(population_size)]

    for _ in range(generations):
        fronts = fast_non_dominated_sort(population)
        for front in fronts:
            crowding_distance(front)

        offspring: list[Individual] = []
        while len(offspring) < population_size:
            parent_a = _tournament(rng, population)
            parent_b = _tournament(rng, population)
            child_priorities = mutate(crossover(parent_a.priorities, parent_b.priorities))
            offspring.append(evaluate(child_priorities))

        combined = population + offspring
        fronts = fast_non_dominated_sort(combined)
        for front in fronts:
            crowding_distance(front)

        next_population: list[Individual] = []
        for front in fronts:
            if len(next_population) + len(front) <= population_size:
                next_population.extend(front)
            else:
                front.sort(key=lambda ind: (-ind.crowding))
                next_population.extend(front[: population_size - len(next_population)])
                break
        population = next_population

    final_fronts = fast_non_dominated_sort(population)
    pareto_front = final_fronts[0] if final_fronts else population
    return sorted(pareto_front, key=lambda ind: ind.objectives[0], reverse=True)


def nsga2_order(
    graph: SmellDependencyGraph,
    impact: dict[SmellId, float],
    discount: float = 0.9,
    population_size: int = DEFAULT_POPULATION_SIZE,
    generations: int = DEFAULT_GENERATIONS,
    seed: int = 20260101,
) -> Ordering:
    """Single-Ordering entry point for the orchestrator's Strategy dispatch
    (module docstring: the impact-maximising member of the final Pareto
    front, since this project's Strategy contract returns one order)."""
    front = nsga2_search(graph, impact, discount, population_size, generations, seed)
    if not front:
        return decode_order(graph, impact)
    return front[0].ordering
