"""In-memory code-property graph for structural retrieval (Software Specification
§5.6, §3.2: "call/dependency/inheritance edges supply the context whose absence
causes architecturally blind edits"). An in-memory graph, not a graph database,
per the spec's own HONESTY NOTE that a graph DB is optional at pilot scale.

Call-edge resolution is name-based (no full type inference), so it can conflate
same-named methods on unrelated classes. This is a deliberate, documented
simplification for v1.0's structural-retrieval component -- the ordering
algorithm (this project's actual contribution) does not depend on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from seqrefactor import _treesitter as ts
from seqrefactor.model import Module, RetrievedChunk


@dataclass
class CodePropertyGraph:
    call_graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    inheritance_graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    snippets: dict[str, str] = field(default_factory=dict)


def build(module: Module) -> CodePropertyGraph:
    cpg = CodePropertyGraph()
    method_by_simple_name: dict[str, list[str]] = {}

    for source_file in module.source_files:
        text = source_file.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for cls in ts.parse_file(source_file):
            cpg.inheritance_graph.add_node(cls.qualified_name)
            for method in cls.methods:
                cpg.call_graph.add_node(method.qualified_name)
                cpg.snippets[method.qualified_name] = "\n".join(
                    lines[method.start_line - 1 : method.end_line]
                )
                method_by_simple_name.setdefault(method.name, []).append(method.qualified_name)

    # Second pass: resolve `foo(...)`-style calls inside each method body to any
    # method sharing that simple name (see module docstring on name-based resolution).
    for source_file in module.source_files:
        for cls in ts.parse_file(source_file):
            for method in cls.methods:
                snippet = cpg.snippets.get(method.qualified_name, "")
                for called_name, targets in method_by_simple_name.items():
                    if called_name == method.name:
                        continue
                    if f"{called_name}(" in snippet:
                        for target in targets:
                            cpg.call_graph.add_edge(method.qualified_name, target)

    return cpg


def structural_context(target_element: str, cpg: CodePropertyGraph, top_k: int = 5) -> list[RetrievedChunk]:
    neighbours: list[str] = []
    if target_element in cpg.call_graph:
        neighbours.extend(cpg.call_graph.successors(target_element))
        neighbours.extend(cpg.call_graph.predecessors(target_element))

    chunks: list[RetrievedChunk] = []
    seen: set[str] = set()
    for element in neighbours:
        if element in seen or element == target_element:
            continue
        seen.add(element)
        chunks.append(
            RetrievedChunk(
                source="structural",
                element=element,
                text=cpg.snippets.get(element, ""),
                score=1.0,
            )
        )
        if len(chunks) >= top_k:
            break
    return chunks


class StructuralRetriever:
    def retrieve(self, target_element: str, module: Module) -> list[RetrievedChunk]:
        cpg = build(module)
        return structural_context(target_element, cpg)
