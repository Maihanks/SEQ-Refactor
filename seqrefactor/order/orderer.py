"""The SEQ-REFACTOR ordering algorithm (Software Specification §7.1, paper Algorithm 1;
Working Brief §2/§3 for the signed-edge tie-break and condensation memoisation).

Priority-queue Kahn traversal unifies dependency safety with impact-first
selection: a smell enters the ready set only when its in-degree reaches
zero (safety, OR-1), and among ready smells the max-heap always yields the
highest-impact one (impact-forward, OR-2). Residual cycles are decomposed
into strongly-connected components by Tarjan's algorithm and escalated for
human review rather than broken automatically (OR-3).

CRITICAL INVARIANT -- safety before priority: no code path in this module
may emit a smell before an unresolved prerequisite, regardless of impact.
This is guarded by the ordering golden test (tests/golden/test_ordering.py).

SIGNED EDGES (Working Brief §2 acceptance check): only PREREQUISITE edges
feed the indegree/topological-constraint computation below -- POSITIVE and
NEGATIVE edges are excluded from feasibility entirely. They instead break
ties among simultaneously-eligible smells of otherwise-equal impact: a smell
with more outstanding positive (co-resolution) mass or negative (cascading)
mass towards still-unresolved smells is preferred, so that co-resolution
opportunities are realised and cascade-risk smells are not left to linger.
This never changes *whether* an order is safe, only the order among
already-safe choices -- exactly the acceptance check's "tie-breaking and
cascade anticipation, never feasibility" requirement.
"""

from __future__ import annotations

import heapq
from collections.abc import Hashable

import networkx as nx

from seqrefactor.model import OperationCounters, Ordering, SmellDependencyGraph, SmellId

CondensationCache = dict[Hashable, list[SmellId]]


def _signed_mass(graph: SmellDependencyGraph) -> dict[SmellId, float]:
    """Per-vertex net signed mass: sum of outgoing POSITIVE + NEGATIVE edge
    probabilities towards other vertices, used only as a tie-break (see module
    docstring) -- never as a feasibility signal."""
    mass: dict[SmellId, float] = {n.id: 0.0 for n in graph.nodes}
    for e in graph.edges:
        if e.polarity in ("positive", "negative") and e.src in mass:
            mass[e.src] += e.probability
    return mass


def _residual_cache_key(residual: nx.DiGraph) -> Hashable:
    """A hashable fingerprint of a residual subgraph's structure, stable across
    steps as long as the same set of vertices and edges persists (Working
    Brief §3: "condense strongly-connected components once with Tarjan and
    memoise the condensation, so a cycle that persists across steps is not
    re-explored each iteration")."""
    return (frozenset(residual.nodes), frozenset(residual.edges))


def order(
    graph: SmellDependencyGraph,
    impact: dict[SmellId, float],
    condensation_cache: CondensationCache | None = None,
) -> Ordering:
    """Compute a dependency-safe, impact-forward agenda plus an escalation set.

    Complexity is ``O((|V| + |E|) log |V|)`` with a binary heap: O(|V|)
    extractions and O(|E|) pushes for the traversal, O(|V| + |E|) for the
    Tarjan decomposition of any residual cycle (skipped entirely on a cache
    hit when ``condensation_cache`` is supplied and the residual is
    unchanged from a previous call).

    ``condensation_cache``, when passed, is mutated in place -- callers that
    want memoisation across steps (Working Brief §3, orchestrator's
    re-planning loop) should hold one dict and pass it to every call.
    """
    counters = OperationCounters()
    prerequisites = [e for e in graph.edges if e.polarity == "prerequisite"]

    g = nx.DiGraph()
    g.add_nodes_from(n.id for n in graph.nodes)
    g.add_edges_from((e.src, e.dst) for e in prerequisites)
    counters.vertex_touches += g.number_of_nodes()
    counters.edge_touches += g.number_of_edges()

    signed_mass = _signed_mass(graph)
    indeg = {v: g.in_degree(v) for v in g}
    # Max-heap via (negated impact, negated signed mass, id) for determinism (NFR-2).
    ready: list[tuple[float, float, SmellId]] = [
        (-impact[v], -signed_mass.get(v, 0.0), v) for v in g if indeg[v] == 0
    ]
    heapq.heapify(ready)
    counters.heap_operations += len(ready)

    agenda: list[SmellId] = []
    while ready:
        _, _, v = heapq.heappop(ready)  # highest-impact eligible smell (tie: signed mass, id)
        counters.heap_operations += 1
        agenda.append(v)
        for w in g.successors(v):
            counters.edge_touches += 1
            indeg[w] -= 1
            if indeg[w] == 0:
                heapq.heappush(ready, (-impact[w], -signed_mass.get(w, 0.0), w))
                counters.heap_operations += 1

    escalations: list[list[SmellId]] = []
    if len(agenda) < g.number_of_nodes():
        emitted = set(agenda)
        residual = g.subgraph(v for v in g if v not in emitted)
        counters.vertex_touches += residual.number_of_nodes()

        for comp in nx.strongly_connected_components(residual):
            if len(comp) > 1:  # a genuine cycle -> escalate, never break automatically
                escalations.append(sorted(comp))

        cache_key = _residual_cache_key(residual) if condensation_cache is not None else None
        if cache_key is not None and cache_key in condensation_cache:
            singleton_order = condensation_cache[cache_key]
        else:
            # Order the acyclic condensation of the residual: its safe (singleton) parts.
            condensation = nx.condensation(residual)
            singleton_order = [
                next(iter(condensation.nodes[scc_node]["members"]))
                for scc_node in nx.topological_sort(condensation)
                if len(condensation.nodes[scc_node]["members"]) == 1
            ]
            counters.order_renumbering_operations += len(singleton_order)
            if cache_key is not None:
                condensation_cache[cache_key] = singleton_order

        agenda.extend(singleton_order)

    return Ordering(agenda=agenda, escalations=escalations, counters=counters)
