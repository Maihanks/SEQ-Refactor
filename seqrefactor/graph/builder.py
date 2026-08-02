"""Smell-dependency graph construction (Software Specification §5.3, §7.3).

Edges come from two complementary, audited sources (OR-5):

1. Catalogue rules -- a category-level precedence (graph/rules.py) fires when
   a prerequisite-category instance structurally contains a dependent-category
   instance (e.g. a GodClass containing the method that is Feature-Envious).
2. Structural co-location -- independent of category, when one instance's
   localisation contains another's, the containing instance is a prerequisite:
   resolving it (e.g. splitting a class) redefines the boundaries the
   contained smell is scoped to.

Containment is the only directional signal used: it is unambiguous (the
container must be restructured for the contained element to have a stable
final shape), unlike two instances that merely share a sibling element,
which carries no reliable direction and is therefore not edged.
"""

from __future__ import annotations

from seqrefactor.graph.rules import rules_for
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


def build(smells: list[SmellInstance], module: Module | None = None) -> SmellDependencyGraph:
    """Build the smell-dependency graph over ``smells`` (Module reserved for future
    structural retrieval sources, e.g. call-graph-derived edges; unused by v1.0 rules)."""
    del module  # interface parity with the SmellGraphBuilder protocol (§5.3)

    edges: list[DepEdge] = []
    for u in smells:
        for v in smells:
            if u.id == v.id:
                continue
            if not _localises_within(u, v):
                continue

            rule = rules_for(u.category, v.category)
            if rule is not None:
                edges.append(DepEdge(src=u.id, dst=v.id, provenance=f"rule:{rule.id}"))
            else:
                shared = next(
                    (
                        f"{oe}~{ie}"
                        for oe in u.loc
                        for ie in v.loc
                        if _contains(oe, ie) and oe != ie
                    ),
                    "",
                )
                edges.append(DepEdge(src=u.id, dst=v.id, provenance=f"structural:{shared}"))

    return SmellDependencyGraph(nodes=list(smells), edges=edges)
