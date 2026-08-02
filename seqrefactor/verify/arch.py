"""Architectural constraint check (Software Specification §5.8): interface surface
and dependency direction (§3.2's "distance from the main sequence and interface
surface" concern).

Two real, if intentionally coarse, checks -- both computed from tree-sitter,
no external tool required:

1. Method-surface check: no method signature (qualified name + parameter
   count) present in a class before the transformation silently vanishes
   from the same class after it. This does not distinguish public from
   private methods (the tree-sitter helper does not currently extract
   modifiers), so it is a surface-STABILITY check, not a strict public-API
   contract check; treat a violation as "a caller of this exact signature
   may now break," not as proof of an ABI break.
2. Package dependency-direction check: a directed package import graph is
   built from `import` declarations before and after; a violation is a
   newly introduced cycle between packages (a pair, or larger set, of
   packages that now depend on each other) that did not exist before --
   the acyclic-dependencies-principle erosion this project's own paper
   motivates avoiding.
"""

from __future__ import annotations

import re

import networkx as nx

from seqrefactor import _treesitter as ts
from seqrefactor.model import ArchResult, Module

_IMPORT_RE = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;", re.MULTILINE)


def _method_surface(module: Module) -> set[str]:
    surface: set[str] = set()
    for cls in ts.parse_module(module.source_files):
        for method in cls.methods:
            surface.add(f"{method.qualified_name}/{method.param_count}")
    return surface


def _package_import_graph(module: Module) -> nx.DiGraph:
    graph = nx.DiGraph()
    for source_file in module.source_files:
        text = source_file.read_text(encoding="utf-8", errors="replace")
        package_match = re.search(r"^\s*package\s+([\w.]+)\s*;", text, re.MULTILINE)
        own_package = package_match.group(1) if package_match else ""
        graph.add_node(own_package)
        for imported in _IMPORT_RE.findall(text):
            imported_package = imported.rsplit(".", 1)[0]
            if imported_package and imported_package != own_package:
                graph.add_edge(own_package, imported_package)
    return graph


def _new_package_cycles(before: nx.DiGraph, after: nx.DiGraph) -> list[list[str]]:
    before_cycles = {
        tuple(sorted(c)) for c in nx.strongly_connected_components(before) if len(c) > 1
    }
    after_cycles = {
        tuple(sorted(c)) for c in nx.strongly_connected_components(after) if len(c) > 1
    }
    return [list(c) for c in sorted(after_cycles - before_cycles)]


class ArchCheck:
    """Implements the ``ArchCheck`` contract (§5.8): ``check(before, after) -> ArchResult``."""

    def check(self, before: Module, after: Module) -> ArchResult:
        violations: list[str] = []

        before_surface = _method_surface(before)
        after_surface = _method_surface(after)
        removed = before_surface - after_surface
        for signature in sorted(removed):
            violations.append(f"method surface shrank: {signature} no longer present")

        new_cycles = _new_package_cycles(_package_import_graph(before), _package_import_graph(after))
        for cycle in new_cycles:
            violations.append(f"new circular package dependency introduced: {' <-> '.join(cycle)}")

        return ArchResult(ok=not violations, violations=violations)
