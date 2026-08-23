"""Deterministic synthetic-subject generator (Working Brief, Phase 2, Section 1 / C-corpus).

Plants each smell as a real, compilable Java structural pattern that the
existing native detector (``detect/native.py``) and graph builder
(``graph/builder.py``) can independently rediscover, rather than declaring
smells only in the manifest. This is what avoids the circularity a reviewer
would otherwise flag (Working Brief §1.1): the ground-truth edges below come
from what was actually written into the generated ``.java`` files, and the
builder is never given the manifest, only the source.

SCOPE NOTE, stated honestly rather than silently narrowed: the native
detector implements exactly four smell categories (class-level GodClass;
method-level LongMethod, MessageChains, BigSwitch, see
``detect/native.py``'s module docstring). It has no Feature Envy, Duplicated
Code, Large Class, Divergent Change, Shotgun Surgery, or Middle Man
detection. Planting those categories here would guarantee zero recall for
them specifically (a detector limitation, not a generator bug) and would
undermine the "substantially overlap" acceptance check the brief itself
asks for. This generator therefore plants only the four detector-supported
categories; extending the native detector to more categories is future
work, not attempted here (matches the same "implement what can be verified,
document what can't" approach used throughout this repository, e.g.
``graph/incremental.py``'s design note on Pearce-Kelly).

CYCLE NOTE: the graph builder's edge derivation (``graph/builder.edge_for_pair``)
is fundamentally containment-based, and containment among real, distinct
source elements is acyclic by construction (a method cannot structurally
contain the class that contains it). A genuine, builder-*discoverable* cycle
from real code is therefore architecturally impossible with the current
builder, not merely hard. Cycle subjects here follow the same pattern
already established by the hand-written ``datasets/synthetic/billing_cycle_v1``
and ``notification_mixed_v1`` fixtures: a manifest-declared cycle, additional
to (not a replacement for) the containment-derived prerequisites, included
specifically to exercise SCC escalation (RQ3), not to be independently
rediscovered by the builder for that specific pair.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

PACKAGE = "synth"

_METHOD_CATEGORIES: list[str] = ["LongMethod", "MessageChains", "BigSwitch"]
_SEVERITY_BASE = {"GodClass": 1.0, "LongMethod": 0.8, "MessageChains": 0.5, "BigSwitch": 0.3}
_SIGNED_OPERATIONS = ["Extract Method", "Hide Delegate", "Rename Method", "Inline Method"]


@dataclass
class _SmellPlan:
    id: str
    category: str
    class_name: str
    method_name: str | None  # None for a class-level (GodClass) smell
    severity: float

    @property
    def qualified_name(self) -> str:
        if self.method_name is None:
            return f"{PACKAGE}.{self.class_name}"
        return f"{PACKAGE}.{self.class_name}.{self.method_name}"


@dataclass
class _ClassPlan:
    name: str
    is_god: bool
    children: list[_SmellPlan] = field(default_factory=list)
    god_smell: _SmellPlan | None = None


@dataclass
class SubjectPlan:
    """The deterministic, seed-derived plan a generated subject follows --
    separated from Java/YAML text assembly so plan generation itself is
    directly unit-testable (Working Brief §1.6, determinism check)."""

    subject_id: str
    seed: int
    classes: list[_ClassPlan]
    all_smells: list[_SmellPlan]
    prerequisites: list[tuple[str, str]]  # (src id, dst id)
    positive_deps: list[tuple[str, str, float, str]]  # (src, dst, probability, operation)
    negative_deps: list[tuple[str, str, float, str]]
    cyclic: bool


def _round_robin_allocate(n_god: int, n_smells: int, n_leaf: int) -> tuple[list[int], int]:
    """Every god container gets >=1 child smell first; remaining budget goes to
    leaf classes (as standalone BigSwitch smells, up to one each) and then any
    further remainder round-robins back onto the god containers."""
    per_god = [1] * n_god
    remaining = n_smells - n_god

    leaf_smell_count = min(n_leaf, max(0, remaining))
    remaining -= leaf_smell_count

    i = 0
    while remaining > 0:
        per_god[i % n_god] += 1
        remaining -= 1
        i += 1

    return per_god, leaf_smell_count


def build_plan(
    subject_id: str,
    seed: int,
    n_classes: int,
    n_smells: int,
    dependency_density: float,
    cycle_rate: float,
    positive_rate: float,
    negative_rate: float,
) -> SubjectPlan:
    """Pure, deterministic planning step (no file I/O): given the same
    arguments, always returns an identical plan (Working Brief §1.6)."""
    rng = random.Random(f"{subject_id}:{seed}")

    n_classes = max(1, n_classes)
    n_smells = max(1, n_smells)
    n_god = max(1, min(n_classes, round(n_classes * dependency_density)))
    n_god = min(n_god, n_smells)  # every god container needs at least one child
    n_leaf = n_classes - n_god

    per_god, n_leaf_smells = _round_robin_allocate(n_god, n_smells, n_leaf)

    classes: list[_ClassPlan] = []
    all_smells: list[_SmellPlan] = []
    prerequisites: list[tuple[str, str]] = []
    counter = 0

    def next_id() -> str:
        nonlocal counter
        counter += 1
        return f"s{counter}"

    for gi in range(n_god):
        class_name = f"GodClass{gi}"
        god_smell = _SmellPlan(
            id=next_id(),
            category="GodClass",
            class_name=class_name,
            method_name=None,
            severity=round(_SEVERITY_BASE["GodClass"] + rng.uniform(-0.0, 0.0), 2),
        )
        all_smells.append(god_smell)
        cls = _ClassPlan(name=class_name, is_god=True, god_smell=god_smell)

        for mi in range(per_god[gi]):
            category = rng.choice(_METHOD_CATEGORIES)
            method_name = f"m{mi}_{category.lower()}"
            smell = _SmellPlan(
                id=next_id(),
                category=category,
                class_name=class_name,
                method_name=method_name,
                severity=round(_SEVERITY_BASE[category] + rng.uniform(-0.05, 0.05), 2),
            )
            cls.children.append(smell)
            all_smells.append(smell)
            prerequisites.append((god_smell.id, smell.id))

        classes.append(cls)

    leaf_class_names = [f"LeafClass{li}" for li in range(n_leaf)]
    for li, class_name in enumerate(leaf_class_names):
        cls = _ClassPlan(name=class_name, is_god=False)
        if li < n_leaf_smells:
            smell = _SmellPlan(
                id=next_id(),
                category="BigSwitch",
                class_name=class_name,
                method_name="leafSwitch",
                severity=round(_SEVERITY_BASE["BigSwitch"], 2),
            )
            cls.children.append(smell)
            all_smells.append(smell)
        classes.append(cls)

    # Positive/negative dependencies: injected ground truth between sibling
    # children of the same god container (Working Brief §1.3's "two chains in
    # the same fan-out"), matching the existing pilot_checkout_v1 pattern --
    # never derived from containment/catalogue, always hand-declared here.
    positive_deps: list[tuple[str, str, float, str]] = []
    negative_deps: list[tuple[str, str, float, str]] = []
    for cls in classes:
        if len(cls.children) < 2:
            continue
        if rng.random() < positive_rate:
            a, b = rng.sample(cls.children, 2)
            positive_deps.append(
                (a.id, b.id, round(rng.uniform(0.3, 0.7), 2), rng.choice(_SIGNED_OPERATIONS))
            )
        if rng.random() < negative_rate:
            a, b = rng.sample(cls.children, 2)
            negative_deps.append(
                (a.id, b.id, round(rng.uniform(0.2, 0.5), 2), rng.choice(_SIGNED_OPERATIONS))
            )

    # A manifest-only cycle (see module docstring's CYCLE NOTE): two distinct
    # method-level smells from (possibly different) god containers, additional
    # to the containment-derived prerequisites above.
    cyclic = False
    method_smells = [s for s in all_smells if s.method_name is not None]
    if rng.random() < cycle_rate and len(method_smells) >= 2:
        a, b = rng.sample(method_smells, 2)
        prerequisites.append((a.id, b.id))
        prerequisites.append((b.id, a.id))
        cyclic = True

    return SubjectPlan(
        subject_id=subject_id,
        seed=seed,
        classes=classes,
        all_smells=all_smells,
        prerequisites=prerequisites,
        positive_deps=positive_deps,
        negative_deps=negative_deps,
        cyclic=cyclic,
    )


# --------------------------------------------------------------------------
# Java source assembly (pure string templates, verified once against the real
# detector's exact thresholds, see detect/native.py's DetectionThresholds and
# _treesitter.py's cyclomatic-complexity/chain-depth/switch-case counting).
# --------------------------------------------------------------------------


def _filler_method(name: str) -> str:
    # complexity=2 (1 base + 1 if), loc=6: comfortably below every smell
    # threshold, but still "substantive" for the GodClass method-count check.
    return f"""
    public int {name}(int x) {{
        if (x > 0) {{
            return x + 1;
        }}
        return x - 1;
    }}
"""


def _long_method(name: str) -> str:
    # loc=16 >= long_method_min_loc(15); no branches (complexity=1), so this
    # is classified purely by length, not by accident of the complexity check.
    return f"""
    public int {name}(int seed) {{
        int total = seed;
        total = total + 1;
        total = total + 2;
        total = total + 3;
        total = total + 4;
        total = total + 5;
        total = total + 6;
        total = total + 7;
        total = total + 8;
        total = total + 9;
        total = total + 10;
        total = total * 2;
        total = total - seed;
        return total;
    }}
"""


def _message_chain_method(name: str) -> str:
    # chain depth 4 (trim -> toLowerCase -> replace -> substring) >= 3.
    return f"""
    public String {name}(String input) {{
        return input.trim().toLowerCase().replace('a', 'b').substring(0, 3);
    }}
"""


def _big_switch_method(name: str) -> str:
    # 4 non-default case labels >= big_switch_min_cases(4).
    return f"""
    public String {name}(int code) {{
        switch (code) {{
            case 0:
                return "zero";
            case 1:
                return "one";
            case 2:
                return "two";
            case 3:
                return "three";
            default:
                return "other";
        }}
    }}
"""


_METHOD_TEMPLATES = {
    "LongMethod": _long_method,
    "MessageChains": _message_chain_method,
    "BigSwitch": _big_switch_method,
}

# (input-args-as-Java-literal, expected-value-as-Java-literal, assertion kind)
_METHOD_TEST_FIXTURES: dict[str, tuple[str, str, Literal["int", "String"]]] = {
    "LongMethod": ("3", "113", "int"),
    "MessageChains": ('" ABCDEF "', '"bbc"', "String"),
    "BigSwitch": ("2", '"two"', "String"),
}


def _god_class_source(cls: _ClassPlan) -> str:
    # Enough fillers to guarantee substantive_methods >= 6 (detect/native.py's
    # GodClass threshold) regardless of how many real smell children this
    # particular container got.
    n_fillers = max(0, 6 - len(cls.children)) + 2
    fillers = "".join(_filler_method(f"filler{i}") for i in range(n_fillers))
    smells = "".join(
        f"\n    // planted: {s.id} ({s.category})" + _METHOD_TEMPLATES[s.category](s.method_name)
        for s in cls.children
    )
    return f"""package {PACKAGE};

/** Generated God Class container (seqrefactor.synth.generator). Deliberately
 * a God Class: {len(cls.children)} planted method-level smell(s) plus filler
 * methods, so it is a real structural prerequisite of each smell it contains
 * (decomposing it would move the methods below). Do not "clean up". */
public class {cls.name} {{
{fillers}{smells}
}}
"""


def _leaf_class_source(cls: _ClassPlan) -> str:
    if not cls.children:
        return f"""package {PACKAGE};

/** Generated leaf class (seqrefactor.synth.generator), no planted smell. */
public class {cls.name} {{

    public int identity(int x) {{
        return x;
    }}
}}
"""
    smell = cls.children[0]
    body = _METHOD_TEMPLATES[smell.category](smell.method_name)
    return f"""package {PACKAGE};

/** Generated leaf class (seqrefactor.synth.generator). {smell.category}
 * planted with no prerequisite: a leaf node in the dependency graph. */
public class {cls.name} {{
{body}
}}
"""


def _test_source(cls: _ClassPlan) -> str:
    method_smells = cls.children
    cases = []
    for s in method_smells:
        arg, expected, _kind = _METHOD_TEST_FIXTURES[s.category]
        cases.append(
            f"""
    @Test
    void {s.method_name}Behaves() {{
        {cls.name} subject = new {cls.name}();
        assertEquals({expected}, subject.{s.method_name}({arg}));
    }}
"""
        )
    if not cases:
        cases.append(
            f"""
    @Test
    void identityIsNoOp() {{
        {cls.name} subject = new {cls.name}();
        assertEquals(5, subject.identity(5));
    }}
"""
        )
    body = "".join(cases)
    return f"""package {PACKAGE};

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class {cls.name}Test {{
{body}
}}
"""


def _manifest_yaml(plan: SubjectPlan) -> str:
    smells = [
        {
            "id": s.id,
            "category": s.category,
            "loc": [s.qualified_name],
            "severity": s.severity,
        }
        for s in plan.all_smells
    ]
    prerequisites = [{"src": src, "dst": dst} for src, dst in plan.prerequisites]
    positive = [
        {"src": src, "dst": dst, "probability": prob, "operation": op}
        for src, dst, prob, op in plan.positive_deps
    ]
    negative = [
        {"src": src, "dst": dst, "probability": prob, "operation": op}
        for src, dst, prob, op in plan.negative_deps
    ]
    doc = {
        "subject": plan.subject_id,
        "acyclic": not plan.cyclic,
        "smells": smells,
        "prerequisites": prerequisites,
        "expected_cascade_if_out_of_order": [
            f"{dst}-before-{src}" for src, dst in plan.prerequisites[: len(plan.classes)]
        ],
    }
    if positive:
        doc["positive_dependencies"] = positive
    if negative:
        doc["negative_dependencies"] = negative

    header = (
        f"# Generated by seqrefactor.synth.generator (seed={plan.seed}). Do not hand-edit,\n"
        f"# regenerate instead: the generator is the source of truth, this file its output.\n"
    )
    return header + yaml.safe_dump(doc, sort_keys=False, default_flow_style=False)


def generate_subject(
    subject_id: str,
    seed: int,
    n_classes: int,
    n_smells: int,
    dependency_density: float,
    cycle_rate: float,
    positive_rate: float,
    negative_rate: float,
    out_root: str = "datasets/synthetic",
) -> str:
    """Write ``<out_root>/<subject_id>/`` with real compilable Java (main +
    test) and a ground-truth manifest.yaml, fully determined by ``seed``.
    Returns the subject directory path.
    """
    plan = build_plan(
        subject_id,
        seed,
        n_classes,
        n_smells,
        dependency_density,
        cycle_rate,
        positive_rate,
        negative_rate,
    )

    root = Path(out_root) / subject_id
    main_dir = root / "src" / "main" / "java" / PACKAGE
    test_dir = root / "src" / "test" / "java" / PACKAGE
    main_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    for cls in plan.classes:
        source = _god_class_source(cls) if cls.is_god else _leaf_class_source(cls)
        (main_dir / f"{cls.name}.java").write_text(source, encoding="utf-8")
        (test_dir / f"{cls.name}Test.java").write_text(_test_source(cls), encoding="utf-8")

    (root / "manifest.yaml").write_text(_manifest_yaml(plan), encoding="utf-8")

    return str(root)
