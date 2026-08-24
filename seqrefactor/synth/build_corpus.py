"""Generate the full synthetic corpus from one master seed (Working Brief, Phase 2
Section 2, extended by Phase 2c Section 2.2's Priority-Dependency Conflict
family). Every subject's own seed is derived deterministically from the master
seed and its index, so the whole corpus is reproducible from a single number.

Two families:

1. The grid (``build_spec_grid``): three size tiers (small/medium/large,
   varying n_classes and n_smells together) crossed with three
   dependency-density levels (low/medium/high), plus explicit cycle subjects
   (RQ3) and a couple of extra high-variety subjects at the top of the size
   range. Since Phase 2c, every grid subject's severity is decorrelated from
   dependency role by ``synth/generator.build_plan`` itself (no change needed
   here to get that property) -- see that module's docstring.
2. The Priority-Dependency Conflict family (``build_conflict_spec_grid``):
   pairs, widths, and chains where a low-severity prerequisite's dependent(s)
   are deliberately higher severity, so impact_only and the dependency-safe
   strategies are forced to diverge by construction (Phase 2c §2.2). These
   are small by nature (2-6 smells) and finish in a handful of orchestrator
   steps regardless of ``max_steps``, so they add little to total run cost
   despite growing subject count.

Subjects are kept deliberately small relative to the brief's suggested 8..25
class range (PHASE2_PLAN.md's cost/scope note): every ablation step costs a
real sidecar compile+test cycle, and this corpus is meant to actually be run
within one session, not just generated.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from seqrefactor.synth.generator import (
    build_chain_plan,
    build_conflict_plan,
    build_plan,
    generate_chain_subject,
    generate_conflict_subject,
    generate_subject,
)

MASTER_SEED = 20260101  # matches seqrefactor.model.Config's own default seed

_SIZES = {
    "small": (5, 6),
    "medium": (8, 11),
    "large": (12, 16),
}
_DENSITIES = {"low": 0.3, "medium": 0.55, "high": 0.8}


@dataclass(frozen=True)
class CorpusSpec:
    subject_id: str
    seed: int
    n_classes: int
    n_smells: int
    dependency_density: float
    cycle_rate: float
    positive_rate: float
    negative_rate: float


def build_spec_grid(master_seed: int = MASTER_SEED) -> list[CorpusSpec]:
    specs: list[CorpusSpec] = []
    index = 0

    def next_seed() -> int:
        nonlocal index
        index += 1
        return master_seed + index

    # 3 sizes x 3 densities = 9 base subjects, no planted cycle.
    for size_name, (n_classes, n_smells) in _SIZES.items():
        for density_name, density in _DENSITIES.items():
            specs.append(
                CorpusSpec(
                    subject_id=f"synth_{size_name}_{density_name}",
                    seed=next_seed(),
                    n_classes=n_classes,
                    n_smells=n_smells,
                    dependency_density=density,
                    cycle_rate=0.0,
                    positive_rate=0.5,
                    negative_rate=0.5,
                )
            )

    # Explicit cycle subjects (RQ3): one per size tier, cycle_rate=1.0 so the
    # plant is deterministic, not probabilistic.
    for size_name, (n_classes, n_smells) in _SIZES.items():
        specs.append(
            CorpusSpec(
                subject_id=f"synth_{size_name}_cycle",
                seed=next_seed(),
                n_classes=n_classes,
                n_smells=n_smells,
                dependency_density=0.6,
                cycle_rate=1.0,
                positive_rate=0.3,
                negative_rate=0.3,
            )
        )

    # A couple of low/high signed-dependency-rate variants (independent of the
    # density grid above), to give the dependency-mass study (Table V) more
    # than one mass profile to compare across subjects.
    specs.append(
        CorpusSpec(
            subject_id="synth_medium_high_signed",
            seed=next_seed(),
            n_classes=8,
            n_smells=11,
            dependency_density=0.55,
            cycle_rate=0.0,
            positive_rate=0.9,
            negative_rate=0.9,
        )
    )
    specs.append(
        CorpusSpec(
            subject_id="synth_medium_low_signed",
            seed=next_seed(),
            n_classes=8,
            n_smells=11,
            dependency_density=0.55,
            cycle_rate=0.0,
            positive_rate=0.1,
            negative_rate=0.1,
        )
    )
    # One larger stress subject beyond the "large" tier, to widen the size range.
    specs.append(
        CorpusSpec(
            subject_id="synth_xlarge_medium",
            seed=next_seed(),
            n_classes=16,
            n_smells=22,
            dependency_density=0.55,
            cycle_rate=0.0,
            positive_rate=0.5,
            negative_rate=0.5,
        )
    )

    return specs


@dataclass(frozen=True)
class ConflictSpec:
    subject_id: str
    seed: int
    kind: str  # "pair" | "width" | "chain"
    width_or_depth: int


def build_conflict_spec_grid(master_seed: int = MASTER_SEED) -> list[ConflictSpec]:
    """Priority-Dependency Conflict family (Working Brief Phase 2c §2.2):
    pairs, widths (1 prerequisite, several dependents), and chains (nested
    prerequisites of increasing depth). A dedicated seed offset
    (``master_seed + 1000 + index``) keeps this family's seeds from ever
    colliding with the grid's, even if either grid grows."""
    specs: list[ConflictSpec] = []
    index = 0

    def next_seed() -> int:
        nonlocal index
        index += 1
        return master_seed + 1000 + index

    for label in ("a", "b", "c"):
        specs.append(ConflictSpec(f"conflict_pair_{label}", next_seed(), "pair", 1))

    for width in (2, 4, 6):
        specs.append(ConflictSpec(f"conflict_width_{width}", next_seed(), "width", width))

    for depth in (2, 3, 4, 5):
        specs.append(ConflictSpec(f"conflict_chain_depth{depth}", next_seed(), "chain", depth))

    return specs


def build_corpus(out_root: str = "datasets/synthetic", master_seed: int = MASTER_SEED) -> list[str]:
    """Generate every subject in both families, returning the list of subject
    directory paths written. Regenerating with the same ``master_seed``
    reproduces the corpus byte-for-byte (each subject's own generation is
    deterministic, see synth/generator.py's own determinism guarantee)."""
    paths = []
    for spec in build_spec_grid(master_seed):
        path = generate_subject(
            subject_id=spec.subject_id,
            seed=spec.seed,
            n_classes=spec.n_classes,
            n_smells=spec.n_smells,
            dependency_density=spec.dependency_density,
            cycle_rate=spec.cycle_rate,
            positive_rate=spec.positive_rate,
            negative_rate=spec.negative_rate,
            out_root=out_root,
        )
        paths.append(path)

    for cspec in build_conflict_spec_grid(master_seed):
        if cspec.kind == "chain":
            path = generate_chain_subject(
                cspec.subject_id, cspec.seed, depth=cspec.width_or_depth, out_root=out_root
            )
        else:
            path = generate_conflict_subject(
                cspec.subject_id, cspec.seed, shape=cspec.kind, width=cspec.width_or_depth,
                out_root=out_root,
            )
        paths.append(path)

    return paths


def write_corpus_md(path: str = "datasets/synthetic/CORPUS.md", master_seed: int = MASTER_SEED) -> None:
    specs = build_spec_grid(master_seed)
    intro = (
        f"Generated by `seqrefactor.synth.build_corpus` from master seed `{master_seed}` "
        "(Working Brief, Phase 2, Section 2). Regenerate with:"
    )
    regen_cmd = (
        "uv run python -c \"from seqrefactor.synth.build_corpus import build_corpus, "
        "write_corpus_md; build_corpus(); write_corpus_md()\""
    )
    sync_note = (
        "Every subject's own seed is `master_seed + index` in grid-definition order "
        "(`build_spec_grid`), so this table and the corpus on disk are always in sync "
        "with the code that produced them, never hand-edited."
    )
    header_row = (
        "| subject | seed | n_classes | n_smells (planted) | dependency_density | "
        "cycle | positive_rate | negative_rate |"
    )
    lines = [
        "# CORPUS.md",
        "",
        intro,
        "",
        "```bash",
        regen_cmd,
        "```",
        "",
        sync_note,
        "",
        header_row,
        "|---|---|---|---|---|---|---|---|",
    ]
    for spec in specs:
        plan = build_plan(
            spec.subject_id, spec.seed, spec.n_classes, spec.n_smells,
            spec.dependency_density, spec.cycle_rate, spec.positive_rate, spec.negative_rate,
        )
        lines.append(
            f"| `{spec.subject_id}` | {spec.seed} | {spec.n_classes} | "
            f"{len(plan.all_smells)} | {spec.dependency_density} | "
            f"{'yes' if plan.cyclic else 'no'} | {spec.positive_rate} | {spec.negative_rate} |"
        )
    scope_note = (
        "Each subject plants only the four smell categories the native detector "
        "(`detect/native.py`) actually supports (GodClass, LongMethod, MessageChains, "
        "BigSwitch) -- see `synth/generator.py`'s module docstring SCOPE NOTE for why "
        "Feature Envy and other catalogue-only categories are not planted. Cycle "
        "subjects (`cycle=yes`) carry a manifest-declared cycle in addition to the "
        "containment-derived prerequisites, exercising SCC escalation (RQ3); see the "
        "generator's CYCLE NOTE for why this cannot instead be made independently "
        "builder-discoverable with the current containment-based edge derivation."
    )
    lines += ["", scope_note]

    conflict_specs = build_conflict_spec_grid(master_seed)
    conflict_intro = (
        "A low-severity God Class prerequisite whose dependent(s) are deliberately "
        "higher severity, planted through real code (padding decouples detection "
        "from severity, see `synth/generator.py`'s PHASE 2C docstring section), so "
        "`impact_only` and the dependency-safe strategies are forced to diverge by "
        "construction, not by chance."
    )
    conflict_header_row = (
        "| subject | seed | kind | width/depth | prerequisite severity | "
        "min dependent severity |"
    )
    lines += [
        "",
        "## Priority-Dependency Conflict family (Working Brief Phase 2c §2.2)",
        "",
        conflict_intro,
        "",
        conflict_header_row,
        "|---|---|---|---|---|---|",
    ]
    for cspec in conflict_specs:
        if cspec.kind == "chain":
            cplan = build_chain_plan(cspec.subject_id, cspec.seed, depth=cspec.width_or_depth)
            god_severities = [s.severity for s in cplan.all_smells if s.category == "GodClass"]
            dep_severities = [s.severity for s in cplan.all_smells if s.category != "GodClass"]
        else:
            cplan = build_conflict_plan(cspec.subject_id, cspec.seed, cspec.kind, cspec.width_or_depth)
            god_severities = [cplan.classes[0].god_smell.severity]
            dep_severities = [c.severity for c in cplan.classes[0].children]
        lines.append(
            f"| `{cspec.subject_id}` | {cspec.seed} | {cspec.kind} | {cspec.width_or_depth} | "
            f"{max(god_severities):.2f} | {min(dep_severities):.2f} |"
        )

    total_note = (
        f"**Total: {len(specs)} grid subjects + {len(conflict_specs)} conflict subjects "
        f"= {len(specs) + len(conflict_specs)} subjects** (Working Brief's Definition of "
        'Done: "at least 15 committed subjects").'
    )
    diamond_note = (
        '"Diamond" shapes (A -> B, A -> C, B -> D, C -> D) are not included: Java\'s '
        "qualified-name namespace is a tree, so no real element can be structurally "
        "contained by two different elements at once -- the same reason genuine cycles "
        "are architecturally impossible for the builder to discover. A diamond could "
        "only be faked as manifest-only ground truth, which would defeat this family's "
        "own purpose (a conflict the detector must independently rediscover), so it is "
        "left out rather than faked; see `synth/generator.py`'s module docstring."
    )
    lines += ["", total_note, "", diamond_note]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
