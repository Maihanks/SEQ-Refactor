"""Five-family metric facade (Software Specification §5.8, §3.2).

Merges two sources exactly as the technology-choice table specifies:

* tree-sitter (in-process) -- cyclomatic complexity and a method-length
  readability proxy, computed directly from source with no external process.
* the CK sidecar (jvm-sidecar) -- CBO (coupling), LCOM (cohesion), and RFC,
  used here as an interface-surface / architecture proxy.

Sign convention: every :class:`~seqrefactor.model.MetricDelta` field is
positive when the change is an IMPROVEMENT (lower coupling/complexity,
higher cohesion, shorter/simpler methods, smaller interface surface),
regardless of whether the underlying raw metric is "lower is better" or
"higher is better" -- this is what seqrefactor.gate reads to fuse Evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from seqrefactor import _sidecar
from seqrefactor import _treesitter as ts
from seqrefactor.model import LocSet, MetricDelta, Module


def _class_of(loc_element: str) -> str:
    """Enclosing class of a dotted loc element (`pkg.Class.method` -> `pkg.Class`).

    Safe for this project's datasets because CK names nested classes with `$`
    (e.g. `orders.Order$LineItem`), never `.`, so the class/method boundary is
    unambiguous under simple dot-splitting.
    """
    return loc_element.rsplit(".", 1)[0] if "." in loc_element else loc_element


@dataclass
class MetricSnapshot:
    ck_by_class: dict[str, dict] = field(default_factory=dict)
    methods_by_qualified_name: dict[str, ts.JavaMethod] = field(default_factory=dict)


def snapshot(module: Module) -> MetricSnapshot:
    ck_rows: list[dict] = []
    if _sidecar.is_available():
        try:
            ck_rows = _sidecar.run_metrics(module.path)
        except _sidecar.SidecarUnavailable:
            ck_rows = []

    methods: dict[str, ts.JavaMethod] = {}
    for cls in ts.parse_module(module.source_files):
        for method in cls.methods:
            methods[method.qualified_name] = method

    return MetricSnapshot(
        ck_by_class={row["class"]: row for row in ck_rows},
        methods_by_qualified_name=methods,
    )


def _relative_improvement(before: float, after: float) -> float:
    """(before - after) / max(before, after); positive means ``after`` is smaller,
    clamped to [-1, 1]. Used uniformly for every "lower raw value is better" metric."""
    denom = max(abs(before), abs(after))
    if denom < 1e-9:
        return 0.0
    return max(-1.0, min(1.0, (before - after) / denom))


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


class MetricFacade:
    """Implements the ``MetricVerifier`` contract (§5.8): ``deltas(before, after, loc)``."""

    def deltas(self, before: Module, after: Module, loc: LocSet) -> MetricDelta:
        before_snap = snapshot(before)
        after_snap = snapshot(after)
        classes = {_class_of(elem) for elem in loc} or set(before_snap.ck_by_class)

        before_cbo = [before_snap.ck_by_class[c]["cbo"] for c in classes if c in before_snap.ck_by_class]
        after_cbo = [after_snap.ck_by_class[c]["cbo"] for c in classes if c in after_snap.ck_by_class]
        before_lcom = [before_snap.ck_by_class[c]["lcom"] for c in classes if c in before_snap.ck_by_class]
        after_lcom = [after_snap.ck_by_class[c]["lcom"] for c in classes if c in after_snap.ck_by_class]
        before_rfc = [before_snap.ck_by_class[c]["rfc"] for c in classes if c in before_snap.ck_by_class]
        after_rfc = [after_snap.ck_by_class[c]["rfc"] for c in classes if c in after_snap.ck_by_class]

        before_methods = [
            m for elem in loc for m in [before_snap.methods_by_qualified_name.get(elem)] if m
        ]
        after_methods = [
            m for elem in loc for m in [after_snap.methods_by_qualified_name.get(elem)] if m
        ]
        before_cc = [m.cyclomatic_complexity for m in before_methods]
        after_cc = [m.cyclomatic_complexity for m in after_methods]
        before_loc_len = [m.loc for m in before_methods]
        after_loc_len = [m.loc for m in after_methods]

        return MetricDelta(
            cohesion=_relative_improvement(_average(before_lcom), _average(after_lcom)),
            coupling=_relative_improvement(_average(before_cbo), _average(after_cbo)),
            complexity=_relative_improvement(_average(before_cc), _average(after_cc)),
            readability=_relative_improvement(_average(before_loc_len), _average(after_loc_len)),
            architecture=_relative_improvement(_average(before_rfc), _average(after_rfc)),
        )
