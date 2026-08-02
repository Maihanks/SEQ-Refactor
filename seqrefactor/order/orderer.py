"""The SEQ-REFACTOR ordering algorithm (Software Specification §7.1, paper Algorithm 1).

Priority-queue Kahn traversal unifies dependency safety with impact-first
selection: a smell enters the ready set only when its in-degree reaches
zero (safety, OR-1), and among ready smells the max-heap always yields the
highest-impact one (impact-forward, OR-2). Residual cycles are decomposed
into strongly-connected components by Tarjan's algorithm and escalated for
human review rather than broken automatically (OR-3).

CRITICAL INVARIANT -- safety before priority: no code path in this module
may emit a smell before an unresolved prerequisite, regardless of impact.
This is guarded by the ordering golden test (tests/golden/test_ordering.py).
"""

from __future__ import annotations

import heapq

import networkx as nx

from seqrefactor.model import Ordering, SmellDependencyGraph, SmellId


def order(graph: SmellDependencyGraph, impact: dict[SmellId, float]) -> Ordering:
    """Compute a dependency-safe, impact-forward agenda plus an escalation set.

    Complexity is ``O((|V| + |E|) log |V|)`` with a binary heap: O(|V|)
    extractions and O(|E|) pushes for the traversal, O(|V| + |E|) for the
    Tarjan decomposition of any residual cycle.
    """
    g = nx.DiGraph()
    g.add_nodes_from(n.id for n in graph.nodes)
    g.add_edges_from((e.src, e.dst) for e in graph.edges)

    indeg = {v: g.in_degree(v) for v in g}
    # Max-heap via negated impact; tie-break on id for determinism (NFR-2).
    ready: list[tuple[float, SmellId]] = [(-impact[v], v) for v in g if indeg[v] == 0]
    heapq.heapify(ready)

    agenda: list[SmellId] = []
    while ready:
        _, v = heapq.heappop(ready)  # highest-impact eligible smell
        agenda.append(v)
        for w in g.successors(v):
            indeg[w] -= 1
            if indeg[w] == 0:
                heapq.heappush(ready, (-impact[w], w))

    escalations: list[list[SmellId]] = []
    if len(agenda) < g.number_of_nodes():
        emitted = set(agenda)
        residual = g.subgraph(v for v in g if v not in emitted)

        for comp in nx.strongly_connected_components(residual):
            if len(comp) > 1:  # a genuine cycle -> escalate, never break automatically
                escalations.append(sorted(comp))

        # Order the acyclic condensation of the residual and append its safe (singleton) parts.
        condensation = nx.condensation(residual)
        for scc_node in nx.topological_sort(condensation):
            members = condensation.nodes[scc_node]["members"]
            if len(members) == 1:
                agenda.append(next(iter(members)))

    return Ordering(agenda=agenda, escalations=escalations)
