"""Shared tree-sitter Java parsing used by both the native SmellDetector and the
tree-sitter half of the metric facade (Software Specification §3.2: "tree-sitter
(in-process)... language-agnostic cyclomatic complexity and structural counts
without a full compiler").

Kept as one module so both consumers walk the same AST shape the same way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import tree_sitter_java as tsjava
from tree_sitter import Language, Node, Parser

_JAVA_LANGUAGE = Language(tsjava.language(), "java")

_DECISION_NODE_TYPES = {
    "if_statement",
    "for_statement",
    "enhanced_for_statement",
    "while_statement",
    "do_statement",
    "catch_clause",
    "switch_label",  # each `case` label under a switch body
    "ternary_expression",
}
_LOGICAL_OPERATORS = {"&&", "||"}


def _parser() -> Parser:
    parser = Parser()
    parser.set_language(_JAVA_LANGUAGE)
    return parser


def _text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _walk(node: Node):
    yield node
    for child in node.children:
        yield from _walk(child)


def _cyclomatic_complexity(node: Node, source: bytes) -> int:
    """McCabe complexity: 1 (base path) + one per decision point in the subtree."""
    complexity = 1
    for n in _walk(node):
        if n.type in _DECISION_NODE_TYPES:
            complexity += 1
        elif n.type == "binary_expression":
            operator = next((c for c in n.children if c.type in _LOGICAL_OPERATORS), None)
            if operator is not None:
                complexity += 1
    return complexity


def _method_invocation_chain_depth(node: Node) -> int:
    """Longest run of nested `a.b().c().d()`-style method_invocation.object chains."""
    if node.type != "method_invocation":
        return 0
    receiver = node.child_by_field_name("object")
    if receiver is None:
        return 1
    return 1 + _method_invocation_chain_depth(receiver)


def _max_chain_depth(node: Node) -> int:
    return max((_method_invocation_chain_depth(n) for n in _walk(node)), default=0)


def _max_switch_case_count(node: Node, source: bytes) -> int:
    """Largest number of `case` (not `default`) labels among switches in ``node``."""
    counts_by_switch: dict[int, int] = {}
    for n in _walk(node):
        if n.type != "switch_label" or _text(n, source).startswith("default"):
            continue
        switch = n
        while switch is not None and switch.type != "switch_expression":
            switch = switch.parent
        key = switch.id if switch is not None else 0
        counts_by_switch[key] = counts_by_switch.get(key, 0) + 1
    return max(counts_by_switch.values(), default=0)


@dataclass
class JavaMethod:
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    param_count: int
    cyclomatic_complexity: int
    max_message_chain_depth: int
    max_switch_case_count: int
    loc: int


@dataclass
class JavaClass:
    name: str
    qualified_name: str
    package: str
    start_line: int
    end_line: int
    field_count: int
    method_count: int
    loc: int
    methods: list[JavaMethod] = field(default_factory=list)


def _qualify(package: str, *parts: str) -> str:
    segments = [p for p in (package, *parts) if p]
    return ".".join(segments)


def _class_name(node: Node, source: bytes) -> str | None:
    name_node = node.child_by_field_name("name")
    return _text(name_node, source) if name_node else None


def parse_file(path: Path) -> list[JavaClass]:
    """Parse a single .java file into its top-level and nested class declarations."""
    source = path.read_bytes()
    tree = _parser().parse(source)
    root = tree.root_node

    package = ""
    pkg_node = next((c for c in root.children if c.type == "package_declaration"), None)
    if pkg_node is not None:
        # package_declaration := 'package' scoped_identifier ';'
        ident = next((c for c in pkg_node.children if c.type in ("scoped_identifier", "identifier")), None)
        if ident is not None:
            package = _text(ident, source)

    classes: list[JavaClass] = []

    def visit_class(node: Node, enclosing: str) -> None:
        name = _class_name(node, source)
        if name is None:
            return
        qualified = _qualify(enclosing) + "." + name if enclosing else _qualify(package, name)
        body = node.child_by_field_name("body")
        methods: list[JavaMethod] = []
        field_count = 0
        if body is not None:
            for child in body.children:
                if child.type == "field_declaration":
                    field_count += sum(1 for c in child.children if c.type == "variable_declarator")
                elif child.type in ("method_declaration", "constructor_declaration"):
                    methods.append(_visit_method(child, qualified, source))
                elif child.type == "class_declaration":
                    visit_class(child, qualified)

        classes.append(
            JavaClass(
                name=name,
                qualified_name=qualified,
                package=package,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                field_count=field_count,
                method_count=len(methods),
                loc=node.end_point[0] - node.start_point[0] + 1,
                methods=methods,
            )
        )

    for top in root.children:
        if top.type == "class_declaration":
            visit_class(top, "")

    return classes


def _visit_method(node: Node, class_qualified_name: str, source: bytes) -> JavaMethod:
    name_node = node.child_by_field_name("name")
    name = _text(name_node, source) if name_node else "<init>"
    params_node = node.child_by_field_name("parameters")
    param_count = 0
    if params_node is not None:
        param_count = sum(1 for c in params_node.children if c.type == "formal_parameter")
    body = node.child_by_field_name("body")
    complexity = _cyclomatic_complexity(body, source) if body is not None else 1
    chain_depth = _max_chain_depth(body) if body is not None else 0
    switch_cases = _max_switch_case_count(body, source) if body is not None else 0
    return JavaMethod(
        name=name,
        qualified_name=f"{class_qualified_name}.{name}",
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        param_count=param_count,
        cyclomatic_complexity=complexity,
        max_message_chain_depth=chain_depth,
        max_switch_case_count=switch_cases,
        loc=node.end_point[0] - node.start_point[0] + 1,
    )


def parse_module(source_files: list[Path]) -> list[JavaClass]:
    classes: list[JavaClass] = []
    for f in source_files:
        classes.extend(parse_file(f))
    return classes


def locate_file(element: str, source_files: list[Path]) -> Path | None:
    """Find the source file whose parsed class qualified-name is a dot-boundary
    prefix of ``element`` (e.g. class `orders.OrderService` contains method
    `orders.OrderService.checkout`). Dot-boundary aware, unlike a plain substring
    check, so `orders.Order` does not spuriously match `orders.OrderService.*`.
    """
    for source_file in source_files:
        for cls in parse_file(source_file):
            if element == cls.qualified_name or element.startswith(cls.qualified_name + "."):
                return source_file
    return None
