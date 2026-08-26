"""Incremental smell-dependency graph maintenance (Working Brief §3 / C6, billed
there as "the headline" contribution; Phase 3c G5 for the construction-cost
framing below).

THE RESULT THIS MODULE ESTABLISHES: an asymptotic improvement in graph
CONSTRUCTION cost, not in sorting. Over a k-step session, rebuilding the
smell-dependency graph from scratch after every accepted step costs
O(k|V|^2) edge derivations (all-pairs, every step); ``apply_step`` below
instead costs O(kd), where d is the size of the disturbed region a single
accepted transformation actually touches -- independent of |V| for a local
refactoring, and recovering the O(k|V|^2) worst case only when a
transformation disturbs the whole module. This is the paper's Proposition 1
("Per-session edge-derivation cost", Section VI-A's bounded-locality
assumptions A1-A3) stated in the notation ``eval/complexity.py`` measures it
in; see that module's docstring for the full statement and
``evaluation/scaling_summary.md`` for the real numbers it produces.

DESIGN NOTE ON WHERE THE SAVING IS, AND ISN'T. Algorithm 1
(``order/orderer.py``) is already a pure function of ``(graph, impact)`` in
``O((|V|+|E|) log|V|)`` time -- cheap by the paper's own complexity analysis
(§V-B: "negligible relative to smell detection, transformation generation,
and verification"), and measured at zero heap and zero reordering operations
in this repo's own scaling study (``evaluation/table4_efficiency.csv``'s
``heap_operations``/``order_renumbering_operations`` columns). Re-running it
on an unchanged graph is therefore not where an "incremental" strategy has
room to win, and pretending otherwise by inventing a bespoke reordering-list
algorithm this repository cannot verify against a reference implementation
would risk exactly the silent-divergence failure mode this module exists to
rule out. The construction cost above -- not the sort -- is the quantity
worth reducing, and it is what this module actually reduces: (1) re-
*detecting* smells over the whole module after every accepted step, when
only the file(s) a transformation touched can have changed, and (2) re-
deriving edges for every O(|V|^2) pair in the module, when only pairs
touching a changed vertex can differ. ``apply_step`` below scopes both to the
disturbed region. Tarjan/condensation memoisation for cycles that persist
across steps lives in ``order/orderer.py`` (``condensation_cache``
parameter), since that is where the condensation is computed.

Because ``apply_step`` is required (and tested, see
``tests/property/test_incremental_equivalence.py``) to produce a graph with
the same node and edge set as calling ``graph.builder.build`` on the same
final pending-smell list, and because ``order/orderer.order`` is a pure
function of the graph, bit-for-bit equivalence between the incremental and
from-scratch execution paths follows by construction, not merely by testing
-- the equivalence harness exists to catch a regression in that construction,
not to establish something that could otherwise go either way.
"""

from __future__ import annotations

from pathlib import Path

from seqrefactor.graph.builder import edge_for_pair
from seqrefactor.model import (
    DepEdge,
    Module,
    OperationCounters,
    SmellDependencyGraph,
    SmellId,
    SmellInstance,
)


def touched_node_ids(nodes: list[SmellInstance], touched_elements: set[str]) -> set[SmellId]:
    """Vertices whose localisation lies inside ``touched_elements`` (the
    qualified class/method names an accepted transformation changed) -- the
    "disturbed region" of Working Brief §3, deliverable 2."""
    ids: set[SmellId] = set()
    for n in nodes:
        for elem in n.loc:
            if any(elem == t or elem.startswith(t + ".") for t in touched_elements):
                ids.add(n.id)
                break
    return ids


def apply_step(
    graph: SmellDependencyGraph,
    resolved_id: SmellId,
    rescanned_smells: list[SmellInstance],
    touched_elements: set[str],
    counters: OperationCounters | None = None,
) -> SmellDependencyGraph:
    """Update ``graph`` after one accepted transformation, touching only the
    disturbed region (Working Brief §3, deliverable 2):

    (a) remove the resolved vertex and its incident edges;
    (b) treat every remaining old vertex localised in ``touched_elements`` as
        stale (its shape may have changed or it may have vanished) and drop
        it too, alongside its incident edges;
    (c) merge in ``rescanned_smells`` -- freshly detected over the disturbed
        region only, never the whole module;
    (d) rebuild edges only for pairs touching a changed (stale-removed or
        newly-added) vertex; edges between two untouched vertices are copied
        from ``graph`` unchanged, never re-derived.

    Returns a new graph; ``graph`` is not mutated. ``counters``, if supplied,
    is updated in place so a caller can accumulate per-step instrumentation
    across a whole run (Working Brief §4).
    """
    counters = counters if counters is not None else OperationCounters()

    stale_ids = touched_node_ids(graph.nodes, touched_elements) | {resolved_id}
    counters.vertex_touches += len(stale_ids) + len(rescanned_smells)

    survivors = [n for n in graph.nodes if n.id not in stale_ids]
    new_nodes = survivors + list(rescanned_smells)
    new_ids = {n.id for n in rescanned_smells}

    kept_edges = [e for e in graph.edges if e.src not in stale_ids and e.dst not in stale_ids]
    counters.edge_touches += len(graph.edges) - len(kept_edges)

    rebuilt_edges: list[DepEdge] = []
    for u in new_nodes:
        for v in new_nodes:
            if u.id == v.id or (u.id not in new_ids and v.id not in new_ids):
                continue  # neither endpoint changed: already covered by kept_edges
            counters.edge_touches += 1
            edge = edge_for_pair(u, v)
            if edge is not None:
                rebuilt_edges.append(edge)

    return SmellDependencyGraph(nodes=new_nodes, edges=kept_edges + rebuilt_edges)


def touched_elements_from_files(files: list[Path]) -> set[str]:
    """Qualified class names declared in ``files``, used as the ``touched_elements``
    scope for ``touched_node_ids`` -- the real-detection adapter's file-to-element
    translation (a smell's ``loc`` entries are qualified class/method names, not
    file paths, so this bridges the two)."""
    from seqrefactor import _treesitter as ts

    return {cls.qualified_name for cls in ts.parse_module(files)}


def rescan_touched_region(module: Module, touched_files: list[Path]) -> list[SmellInstance]:
    """Real-detection adapter (Working Brief §3, deliverable 2b): scope the
    native detector to just the file(s) an accepted transformation touched,
    rather than re-detecting the whole module."""
    from seqrefactor.detect import native as detect_native

    scoped = module.model_copy(update={"source_files": list(touched_files)})
    return detect_native.detect(scoped)
