"""Deterministic synthetic-subject generator (Working Brief, Phase 2/2c).

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
work, not attempted here.

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

PHASE 2C, SEVERITY/IMPACT DESIGN (the working brief this module now
implements). Phase 2's generator gave every God Class the maximum severity
(1.0) deterministically, which made God Class impact-dominant almost always
-- even ``impact_only`` (which ignores dependency edges) tended to pick it
first anyway, so the ordering strategies rarely had a reason to diverge and
H1/H2 came back degenerate. This version decorrelates severity from
dependency role: a prerequisite (God Class) samples its severity from
Uniform(0.2, 0.6); each dependent (method-level smell) it contains samples
independently from Uniform(0.6, 1.0). The two ranges are disjoint except at
their shared boundary, so a prerequisite is *almost always* the least severe
smell in its own group, by construction, not by hope.

Severity is not a manifest-only label here: the real detector
(``detect/native.py``) computes it live from actual code structure --
``min(1.0, substantive_methods / 12)`` for a God Class, ``min(1.0,
cyclomatic_complexity / 10)`` for a method-level smell -- so a target
severity has to be reached by shaping the *code*, not by writing a number
into YAML. Two structural levers make this possible without disturbing
which smell gets detected as which category:

- God Class: detection fires on ``substantive_methods >= 6`` OR
  ``class loc >= 100``. A fixed 100-line padding comment block is added to
  every God Class body, so the loc path always fires regardless of method
  count -- decoupling "is this detected as a God Class at all" from "how
  many substantive methods does it have" (the sole severity driver), which
  is what lets a God Class's severity go below the old implicit floor of
  0.5 (6 substantive methods / 12).
- LongMethod: detection fires on ``loc >= 15`` OR ``complexity >= 6``. A
  fixed block of complexity-free padding statements guarantees ``loc >= 15``
  regardless of how many decision branches follow, so complexity (and
  therefore severity) can be dialled from 1 up to 10 independently of
  whether the method gets detected as LongMethod at all.
- MessageChains: complexity is 1 by construction (a chain has no decision
  points), so it already spans low severity without extra work; additional
  always-true ``if`` branches raise it toward 1.0 when a *high*-severity
  dependent is needed.
- BigSwitch has a structural floor: detection requires >=4 non-default
  cases, and each case is itself a decision point, so the minimum possible
  complexity is 6 (severity 0.6). BigSwitch is therefore only ever used
  here as a dependent (its role in every existing prerequisite structure),
  never as the low-severity prerequisite side of a conflict -- stated
  plainly rather than silently avoided.

PRIORITY-DEPENDENCY CONFLICT FAMILY (Working Brief 2c §2.2). A "pair" or
"width" conflict is exactly a grid-style subject with one God Class
container: ``build_plan`` already produces one whenever ``n_classes`` (god
containers only, no leaf classes) is small, so no separate code path is
needed for those two shapes -- see ``build_conflict_plan``. A "chain"
(A -> B -> C -> ...) needs genuine multi-level containment, realised here as
nested static classes (see ``build_chain_plan`` / ``_chain_source``): each
intermediate level is an independently-detected, low-severity God Class,
and the innermost level is a high-severity method-level smell. A "diamond"
(A -> B, A -> C, B -> D, C -> D) is not attempted: Java's qualified-name
namespace is a tree (each element has exactly one structural parent), so no
element can be structurally contained by two different elements at once --
the same reason genuine cycles are architecturally impossible for the
builder to discover (see CYCLE NOTE above). A diamond could only be
faked as manifest-only ground truth, which would violate this family's own
purpose (a conflict the *detector* must independently rediscover); it is
left out rather than faked.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PACKAGE = "synth"

_METHOD_CATEGORIES: list[str] = ["LongMethod", "MessageChains", "BigSwitch"]
_SIGNED_OPERATIONS = ["Extract Method", "Hide Delegate", "Rename Method", "Inline Method"]

# Test argument used throughout: large enough that every "always-true, relative
# to this argument" branch condition in the templates below genuinely fires,
# for any parameter value this generator ever chooses (max complexity ~10).
_TEST_INT_ARG = 50
_TEST_STRING_ARG = " ABCDEF "  # length 8; base chain result is always "bbc"

_GOD_PADDING_LINES = 100  # guarantees class loc >= 100 regardless of method count
_LONGMETHOD_PADDING_LINES = 11  # guarantees method loc >= 15 regardless of branch count


# --------------------------------------------------------------------------
# Severity <-> structural-parameter conversion (the live detector's own
# formulas, inverted; see module docstring PHASE 2C section).
# --------------------------------------------------------------------------


def severity_from_god_param(n_substantive: int) -> float:
    return round(min(1.0, n_substantive / 12), 3)


def severity_from_method_param(complexity: int) -> float:
    return round(min(1.0, complexity / 10), 3)


def god_param_from_severity(severity: float) -> int:
    return max(1, round(severity * 12))


def method_param_from_severity(severity: float) -> int:
    return max(1, round(severity * 10))


@dataclass
class _SmellPlan:
    id: str
    category: str
    class_name: str  # dotted for nested classes, e.g. "Outer.Inner"
    method_name: str | None  # None for a class-level (GodClass) smell
    severity: float
    param: int  # substantive-method count (GodClass) or target complexity (method-level)

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


def _substantive_contribution(category: str, param: int) -> bool:
    """Whether a method with this category/param counts as "substantive" for
    its containing God Class's own method-count (a secondary effect of the
    param choice below, not something callers need to reason about)."""
    if category == "LongMethod":
        return True  # loc padding guarantees loc >= 15 regardless of param
    if category == "BigSwitch":
        return True  # complexity floor is 6 regardless of param
    if category == "MessageChains":
        return param >= 1  # complexity > 1 only once at least one extra branch is added
    return False


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
    arguments, always returns an identical plan (Working Brief §1.6).

    Severity is decorrelated from dependency role (Working Brief 2c §2.1):
    every God Class samples from Uniform(0.2, 0.6); every method-level smell
    it contains samples independently from Uniform(0.6, 1.0). A subject with
    ``n_classes == 1`` and no leaf classes (dependency_density == 1.0) is
    exactly a Priority-Dependency Conflict "pair" or "width" subject -- see
    ``build_conflict_plan``, which is a thin wrapper choosing exactly those
    parameters.
    """
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
        god_severity = round(rng.uniform(0.2, 0.6), 3)
        god_param = god_param_from_severity(god_severity)
        god_smell = _SmellPlan(
            id=next_id(),
            category="GodClass",
            class_name=class_name,
            method_name=None,
            severity=severity_from_god_param(god_param),
            param=god_param,
        )
        all_smells.append(god_smell)
        cls = _ClassPlan(name=class_name, is_god=True, god_smell=god_smell)

        for mi in range(per_god[gi]):
            category = rng.choice(_METHOD_CATEGORIES)
            method_name = f"m{mi}_{category.lower()}"
            dep_severity = round(rng.uniform(0.6, 1.0), 3)
            method_param = method_param_from_severity(dep_severity)
            smell = _SmellPlan(
                id=next_id(),
                category=category,
                class_name=class_name,
                method_name=method_name,
                severity=severity_from_method_param(method_param),
                param=method_param,
            )
            cls.children.append(smell)
            all_smells.append(smell)
            prerequisites.append((god_smell.id, smell.id))

        classes.append(cls)

    leaf_class_names = [f"LeafClass{li}" for li in range(n_leaf)]
    for li, class_name in enumerate(leaf_class_names):
        cls = _ClassPlan(name=class_name, is_god=False)
        if li < n_leaf_smells:
            leaf_severity = round(rng.uniform(0.3, 0.9), 3)
            leaf_param = method_param_from_severity(leaf_severity)
            smell = _SmellPlan(
                id=next_id(),
                category="BigSwitch",
                class_name=class_name,
                method_name="leafSwitch",
                severity=severity_from_method_param(leaf_param),
                param=leaf_param,
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


def build_conflict_plan(subject_id: str, seed: int, shape: str, width: int = 1) -> SubjectPlan:
    """Priority-Dependency Conflict "pair" (``width=1``) or "width" (``width>1``)
    subject (Working Brief 2c §2.2): exactly one God Class prerequisite
    (severity floor-biased low via a fixed low-end draw) with ``width``
    dependents (severity ceiling-biased high). Reuses ``build_plan`` entirely
    -- a single-god-container, no-leaf-class subject *is* this family, not an
    approximation of it.
    """
    del shape  # kept for call-site readability ("pair" vs "width"); both go through build_plan
    return build_plan(
        subject_id,
        seed,
        n_classes=1,
        n_smells=width,
        dependency_density=1.0,
        cycle_rate=0.0,
        positive_rate=0.0,
        negative_rate=0.0,
    )


def build_chain_plan(subject_id: str, seed: int, depth: int) -> SubjectPlan:
    """Priority-Dependency Conflict "chain" subject (Working Brief 2c §2.2):
    ``depth - 1`` nested, independently-detected low-severity God Classes,
    each containing the next, with a single high-severity method-level smell
    innermost. ``depth=2`` is a plain pair (one God Class, one method smell);
    ``depth>=3`` genuinely nests (God Class contains God Class contains ...).
    """
    rng = random.Random(f"{subject_id}:{seed}:chain")
    depth = max(2, depth)

    classes: list[_ClassPlan] = []
    all_smells: list[_SmellPlan] = []
    prerequisites: list[tuple[str, str]] = []
    counter = 0

    def next_id() -> str:
        nonlocal counter
        counter += 1
        return f"s{counter}"

    dotted_path: list[str] = []
    prior_smell_ids: list[str] = []

    for level in range(depth - 1):
        dotted_path.append(f"Level{level}")
        class_name = ".".join(dotted_path)
        severity = round(rng.uniform(0.2, 0.5), 3)  # each level a bit more room than the pair range
        param = god_param_from_severity(severity)
        smell = _SmellPlan(
            id=next_id(),
            category="GodClass",
            class_name=class_name,
            method_name=None,
            severity=severity_from_god_param(param),
            param=param,
        )
        all_smells.append(smell)
        classes.append(_ClassPlan(name=class_name, is_god=True, god_smell=smell))
        for prior_id in prior_smell_ids:
            prerequisites.append((prior_id, smell.id))
        prior_smell_ids.append(smell.id)

    # Innermost: a high-severity method-level smell inside the deepest God Class
    # (`classes[-1]`), not a further nesting level -- its qualified name is that
    # class's own dotted path plus the method name, matching exactly where
    # `_chain_source` actually writes it (directly inside the last level's body).
    innermost_class_name = ".".join(dotted_path)
    category = rng.choice(_METHOD_CATEGORIES)
    dep_severity = round(rng.uniform(0.8, 1.0), 3)  # top of the range: the chain's whole point
    method_param = method_param_from_severity(dep_severity)
    method_smell = _SmellPlan(
        id=next_id(),
        category=category,
        class_name=innermost_class_name,
        method_name="leafMethod",
        severity=severity_from_method_param(method_param),
        param=method_param,
    )
    all_smells.append(method_smell)
    for prior_id in prior_smell_ids:
        prerequisites.append((prior_id, method_smell.id))

    classes[-1].children.append(method_smell)

    return SubjectPlan(
        subject_id=subject_id,
        seed=seed,
        classes=classes,
        all_smells=all_smells,
        prerequisites=prerequisites,
        positive_deps=[],
        negative_deps=[],
        cyclic=False,
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


def _god_padding() -> str:
    lines = "\n".join(f"    // padding {i}" for i in range(_GOD_PADDING_LINES))
    return lines + "\n"


def _long_method(name: str, complexity: int) -> str:
    k = max(0, complexity - 1)
    padding = "\n".join(f"        total = total + {i};" for i in range(1, _LONGMETHOD_PADDING_LINES + 1))
    branches = "\n".join(
        f"        if (seed >= 0) {{ total = total + {100 + i}; }}" for i in range(k)
    )
    return f"""
    public int {name}(int seed) {{
        int total = seed;
{padding}
{branches}
        return total;
    }}
"""


def _long_method_expected(complexity: int) -> int:
    k = max(0, complexity - 1)
    padding_sum = sum(range(1, _LONGMETHOD_PADDING_LINES + 1))
    branch_sum = sum(100 + i for i in range(k))
    return _TEST_INT_ARG + padding_sum + branch_sum


def _message_chain_method(name: str, complexity: int) -> str:
    k = max(0, complexity - 1)
    branches = "\n".join(
        '        if (input.length() >= 0) { result = result + "x"; }' for _ in range(k)
    )
    return f"""
    public String {name}(String input) {{
        String result = input.trim().toLowerCase().replace('a', 'b').substring(0, 3);
{branches}
        return result;
    }}
"""


def _message_chain_expected(complexity: int) -> str:
    k = max(0, complexity - 1)
    return "bbc" + "x" * k


def _big_switch_method(name: str, complexity: int) -> str:
    case_count = max(4, complexity - 2)
    cases = "\n".join(f'            case {i}: return "v{i}";' for i in range(case_count))
    return f"""
    public String {name}(int code) {{
        switch (code) {{
{cases}
            default: return "other";
        }}
    }}
"""


def _big_switch_expected(complexity: int) -> str:
    del complexity  # test always probes case 2, always present (case_count >= 4)
    return "v2"


_METHOD_TEMPLATES = {
    "LongMethod": _long_method,
    "MessageChains": _message_chain_method,
    "BigSwitch": _big_switch_method,
}


def _test_fixture(category: str, param: int) -> tuple[str, str]:
    """(test-argument-as-Java-literal, expected-value-as-Java-literal)."""
    if category == "LongMethod":
        return str(_TEST_INT_ARG), str(_long_method_expected(param))
    if category == "MessageChains":
        return f'"{_TEST_STRING_ARG}"', f'"{_message_chain_expected(param)}"'
    if category == "BigSwitch":
        return "2", f'"{_big_switch_expected(param)}"'
    raise ValueError(f"no test fixture for category {category!r}")


def _method_body(smell: _SmellPlan) -> str:
    return _METHOD_TEMPLATES[smell.category](smell.method_name, smell.param)


def _god_class_source(cls: _ClassPlan) -> str:
    assert cls.god_smell is not None
    actual_substantive = sum(
        1 for s in cls.children if _substantive_contribution(s.category, s.param)
    )
    n_fillers = max(0, cls.god_smell.param - actual_substantive)
    fillers = "".join(_filler_method(f"filler{i}") for i in range(n_fillers))
    smells = "".join(
        f"\n    // planted: {s.id} ({s.category}, severity {s.severity})" + _method_body(s)
        for s in cls.children
    )
    simple_name = cls.name.split(".")[-1]
    return f"""package {PACKAGE};

/** Generated God Class container (seqrefactor.synth.generator, severity
 * {cls.god_smell.severity}). Deliberately a God Class: {len(cls.children)}
 * planted method-level smell(s) plus filler methods and a fixed padding
 * block (decouples detection from severity, see module docstring), so it
 * is a real structural prerequisite of each smell it contains. Do not
 * "clean up". */
public class {simple_name} {{
{_god_padding()}{fillers}{smells}
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
    body = _method_body(smell)
    return f"""package {PACKAGE};

/** Generated leaf class (seqrefactor.synth.generator). {smell.category}
 * (severity {smell.severity}) planted with no prerequisite: a leaf node in
 * the dependency graph. */
public class {cls.name} {{
{body}
}}
"""


def _test_source(cls: _ClassPlan) -> str:
    method_smells = cls.children
    simple_name = cls.name.split(".")[-1]
    cases = []
    for s in method_smells:
        arg, expected = _test_fixture(s.category, s.param)
        cases.append(
            f"""
    @Test
    void {s.method_name}Behaves() {{
        {simple_name} subject = new {simple_name}();
        assertEquals({expected}, subject.{s.method_name}({arg}));
    }}
"""
        )
    if not cases:
        cases.append(
            f"""
    @Test
    void identityIsNoOp() {{
        {simple_name} subject = new {simple_name}();
        assertEquals(5, subject.identity(5));
    }}
"""
        )
    body = "".join(cases)
    return f"""package {PACKAGE};

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class {simple_name}Test {{
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


def _write_plan(plan: SubjectPlan, out_root: str, nested: bool) -> str:
    root = Path(out_root) / plan.subject_id
    main_dir = root / "src" / "main" / "java" / PACKAGE
    test_dir = root / "src" / "test" / "java" / PACKAGE
    main_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    if not nested:
        for cls in plan.classes:
            source = _god_class_source(cls) if cls.is_god else _leaf_class_source(cls)
            (main_dir / f"{cls.name}.java").write_text(source, encoding="utf-8")
            (test_dir / f"{cls.name}Test.java").write_text(_test_source(cls), encoding="utf-8")
    else:
        source, test_source, outer_name = _chain_source(plan.classes)
        (main_dir / f"{outer_name}.java").write_text(source, encoding="utf-8")
        (test_dir / f"{outer_name}Test.java").write_text(test_source, encoding="utf-8")

    (root / "manifest.yaml").write_text(_manifest_yaml(plan), encoding="utf-8")
    return str(root)


def _chain_source(classes: list[_ClassPlan]) -> tuple[str, str, str]:
    """Emit one file with genuinely nested static classes (Working Brief 2c
    §2.2's "chain": A -> B -> C -> ...), innermost-out. The first level *is*
    the top-level file class (Java forbids a nested class sharing its
    enclosing class's simple name, so there is no separate wrapper); every
    further level nests as a ``public static class`` inside the previous
    one. Returns (main source, test source, outermost class simple name)."""
    outer_name = classes[0].name.split(".")[0]

    def emit(level: int) -> str:
        cls = classes[level]
        simple_name = cls.name.split(".")[-1]
        god = cls.god_smell
        assert god is not None
        is_innermost = level == len(classes) - 1

        if is_innermost:
            actual_substantive = sum(
                1 for s in cls.children if _substantive_contribution(s.category, s.param)
            )
            n_fillers = max(0, god.param - actual_substantive)
            fillers = "".join(_filler_method(f"filler{i}") for i in range(n_fillers))
            smells = "".join(
                f"\n        // planted: {s.id} ({s.category}, severity {s.severity})"
                + _method_body(s)
                for s in cls.children
            )
            inner = ""
        else:
            fillers = "".join(_filler_method(f"filler{i}") for i in range(god.param))
            smells = ""
            inner = emit(level + 1)

        if level == 0:
            return f"""package {PACKAGE};

/** Generated Priority-Dependency Conflict chain (seqrefactor.synth.generator,
 * severity {god.severity}), level 0 of {len(classes)}: each level is a real
 * structural prerequisite of the next, ending in a high-severity
 * method-level smell. Do not "clean up". */
public class {simple_name} {{
{_god_padding()}{fillers}{smells}
{inner}
}}
"""
        return f"""
    /** Nested God Class (severity {god.severity}), level {level}. */
    public static class {simple_name} {{
{_god_padding()}{fillers}{smells}
{inner}
    }}
"""

    main_source = emit(0)

    # Test constructs the innermost class via its fully-qualified nested path
    # and asserts on the leaf method, the only method smell in the chain.
    leaf_cls = classes[-1]
    leaf_smell = leaf_cls.children[0]
    nested_path = ".".join(c.name.split(".")[-1] for c in classes)
    arg, expected = _test_fixture(leaf_smell.category, leaf_smell.param)
    test_source = f"""package {PACKAGE};

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class {outer_name}Test {{

    @Test
    void {leaf_smell.method_name}Behaves() {{
        {nested_path} subject = new {nested_path}();
        assertEquals({expected}, subject.{leaf_smell.method_name}({arg}));
    }}
}}
"""
    return main_source, test_source, outer_name


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
    return _write_plan(plan, out_root, nested=False)


def generate_conflict_subject(
    subject_id: str, seed: int, shape: str, width: int = 1, out_root: str = "datasets/synthetic"
) -> str:
    """Write a Priority-Dependency Conflict "pair" or "width" subject
    (Working Brief 2c §2.2)."""
    plan = build_conflict_plan(subject_id, seed, shape, width)
    return _write_plan(plan, out_root, nested=False)


def generate_chain_subject(
    subject_id: str, seed: int, depth: int, out_root: str = "datasets/synthetic"
) -> str:
    """Write a Priority-Dependency Conflict "chain" subject (Working Brief 2c
    §2.2): nested God Classes, depth-1 of them, ending in one high-severity
    method-level smell."""
    plan = build_chain_plan(subject_id, seed, depth)
    return _write_plan(plan, out_root, nested=True)
