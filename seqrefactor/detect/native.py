"""Native, self-contained SmellDetector (Software Specification §5.2).

Wraps no external analyser; it is a threshold-based heuristic detector built
directly on the tree-sitter parse (seqrefactor._treesitter), so the pipeline
runs end to end with no installed toolchain beyond Python. It implements the
same ``SmellDetector`` contract that a SonarQube/PMD adapter would
(seqrefactor.detect.sonar), so it is a drop-in, swappable component (§1.3
Non-Goals: "not a new smell detector" -- thresholds are a modelling choice,
not a claim of state-of-the-art detection accuracy).

Each method is assigned at most one method-level category, checked in the
priority order below (a method can plausibly exhibit more than one smell;
this detector reports the most structurally significant one it finds rather
than every co-occurring label):

1. BigSwitch      -- a switch with many branches indicates dispatch logic
                     that should be polymorphism; checked first because a
                     wide switch dominates a method's shape.
2. MessageChains   -- a long `a.b().c().d()` receiver chain, checked next
                     since it is a distinct structural pattern independent
                     of method length.
3. LongMethod      -- falls back to the general size/complexity signal.

GodClass is a class-level judgement independent of the method-level pass.
"""

from __future__ import annotations

from dataclasses import dataclass

from seqrefactor import _treesitter as ts
from seqrefactor.model import Module, SmellInstance


@dataclass(frozen=True)
class DetectionThresholds:
    god_class_min_methods: int = 6
    god_class_min_loc: int = 100
    big_switch_min_cases: int = 4
    message_chain_min_depth: int = 3
    long_method_min_loc: int = 15
    long_method_min_complexity: int = 6


DEFAULT_THRESHOLDS = DetectionThresholds()


def _classify_method(method: ts.JavaMethod, thresholds: DetectionThresholds) -> str | None:
    if method.max_message_chain_depth >= thresholds.message_chain_min_depth:
        return "MessageChains"
    if method.loc >= thresholds.long_method_min_loc or (
        method.cyclomatic_complexity >= thresholds.long_method_min_complexity
    ):
        return "LongMethod"
    return None


def _stable_id(category: str, loc: list[str]) -> str:
    """Content-derived, not sequential: stable across re-detection passes (OR-4), so the
    orchestrator's re-detect loop can tell "still present," "resolved," and "newly
    introduced" apart by identity rather than by an arbitrary per-call counter."""
    return f"{category}:{loc[0]}" if loc else category


def detect(module: Module, thresholds: DetectionThresholds = DEFAULT_THRESHOLDS) -> list[SmellInstance]:
    classes = ts.parse_module(module.source_files)
    smells: list[SmellInstance] = []

    for cls in classes:
        # Trivial accessors (no branching and short) are excluded from the count: a data
        # class with many one-line getters/setters is not a God Class, and counting them
        # produces false positives on plain value objects (see tests/unit/test_detect_native.py).
        substantive_methods = sum(
            1 for m in cls.methods if m.cyclomatic_complexity > 1 or m.loc > 5
        )
        if substantive_methods >= thresholds.god_class_min_methods or cls.loc >= thresholds.god_class_min_loc:
            severity = min(1.0, substantive_methods / (thresholds.god_class_min_methods * 2))
            loc = [cls.qualified_name]
            smells.append(
                SmellInstance(
                    id=_stable_id("GodClass", loc),
                    category="GodClass",
                    loc=loc,
                    severity=max(0.1, severity),
                )
            )

        for method in cls.methods:
            if method.max_switch_case_count >= thresholds.big_switch_min_cases:
                category = "BigSwitch"
            else:
                category = _classify_method(method, thresholds)
            if category is None:
                continue
            severity = min(1.0, method.cyclomatic_complexity / 10.0)
            loc = [method.qualified_name]
            smells.append(
                SmellInstance(
                    id=_stable_id(category, loc),
                    category=category,
                    loc=loc,
                    severity=max(0.1, severity),
                )
            )

    return smells
