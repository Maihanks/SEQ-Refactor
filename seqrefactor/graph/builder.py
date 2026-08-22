"""Smell-dependency graph construction (Software Specification §5.3, §7.3;
Working Brief §2 for the signed positive/negative extension).

Edges come from three complementary, audited sources (OR-5), checked in this
priority order for every co-located pair:

1. Catalogue prerequisite rules -- a category-level precedence
   (graph/rules.py PRECEDENCE_RULES) fires when a prerequisite-category
   instance structurally contains a dependent-category instance (e.g. a
   GodClass containing the method that is Feature-Envious). Hard: PREREQUISITE.
2. Signed catalogue rules -- a disjoint category-level table
   (graph/rules.py SIGNED_DEPENDENCY_RULES) of POSITIVE (co-resolution) and
   NEGATIVE (cascading) relations between co-located instances. Soft: never
   gates ordering feasibility (see order/orderer.py), only tie-breaking.
3. Structural co-location fallback -- independent of category, when one
   instance's localisation contains another's and neither rule table above
   matched, the containing instance is still a prerequisite: resolving it
   (e.g. splitting a class) redefines the boundaries the contained smell is
   scoped to. Hard: PREREQUISITE.

Containment is the only directional signal used: it is unambiguous (the
container must be restructured for the contained element to have a stable
final shape), unlike two instances that merely share a sibling element,
which carries no reliable direction and is therefore not edged.
"""

from __future__ import annotations

from seqrefactor.graph.rules import rules_for, signed_rule_for
from seqrefactor.model import DepEdge, Module, SmellDependencyGraph, SmellInstance


def _contains(container: str, member: str) -> bool:
    """True if code element ``member`` lies within ``container`` (dotted-path containment)."""
    return member == container or member.startswith(container + ".")


def _localises_within(outer: SmellInstance, inner: SmellInstance) -> bool:
    """True if some element of ``outer``'s loc set structurally contains one of ``inner``'s."""
    return any(
        _contains(outer_elem, inner_elem) and outer_elem != inner_elem
        for outer_elem in outer.loc
        for inner_elem in inner.loc
    )


def edge_for_pair(u: SmellInstance, v: SmellInstance) -> DepEdge | None:
    """Derive the (at most one) edge from ``u`` to ``v``, if any, following the
    three-source priority order in the module docstring. Factored out of
    ``build`` so ``graph/incremental.py`` can recompute edges for a single
    changed pair without re-deriving the whole graph (Working Brief §3)."""
    if u.id == v.id or not _localises_within(u, v):
        return None

    rule = rules_for(u.category, v.category)
    if rule is not None:
        return DepEdge(src=u.id, dst=v.id, provenance=f"rule:{rule.id}", polarity="prerequisite")

    signed = signed_rule_for(u.category, v.category)
    if signed is not None:
        return DepEdge(
            src=u.id,
            dst=v.id,
            provenance=f"signed:{signed.id}",
            polarity=signed.polarity,
            probability=signed.probability,
            inducing_operation=signed.operation,
        )

    shared = next(
        (f"{oe}~{ie}" for oe in u.loc for ie in v.loc if _contains(oe, ie) and oe != ie),
        "",
    )
    return DepEdge(
        src=u.id, dst=v.id, provenance=f"structural:{shared}", polarity="prerequisite"
    )


def build(smells: list[SmellInstance], module: Module | None = None) -> SmellDependencyGraph:
    """Build the smell-dependency graph over ``smells`` (Module reserved for future
    structural retrieval sources, e.g. call-graph-derived edges; unused by v1.0 rules)."""
    del module  # interface parity with the SmellGraphBuilder protocol (§5.3)

    edges: list[DepEdge] = []
    for u in smells:
        for v in smells:
            edge = edge_for_pair(u, v)
            if edge is not None:
                edges.append(edge)

    return SmellDependencyGraph(nodes=list(smells), edges=edges)
