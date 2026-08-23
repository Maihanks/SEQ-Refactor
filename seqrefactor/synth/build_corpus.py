"""Generate the full synthetic corpus from one master seed (Working Brief, Phase 2,
Section 2). Every subject's own seed is derived deterministically from the master
seed and its index, so the whole corpus is reproducible from a single number.

Grid, documented here (and mirrored into CORPUS.md by ``write_corpus_md``): three
size tiers (small/medium/large, varying n_classes and n_smells together) crossed
with three dependency-density levels (low/medium/high), plus explicit cycle
subjects (RQ3) and a couple of extra high-variety subjects at the top of the size
range. Subjects are kept deliberately small relative to the brief's suggested
8..25 class range (PHASE2_PLAN.md's cost/scope note): every ablation step costs a
real sidecar compile+test cycle, and this corpus is meant to actually be run
within one session, not just generated.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from seqrefactor.synth.generator import build_plan, generate_subject

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


def build_corpus(out_root: str = "datasets/synthetic", master_seed: int = MASTER_SEED) -> list[str]:
    """Generate every subject in the grid, returning the list of subject
    directory paths written. Regenerating with the same ``master_seed`` and
    grid reproduces the corpus byte-for-byte (each subject's own generation is
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
    total_note = (
        f"**Total: {len(specs)} subjects** (Working Brief's Definition of Done: "
        '"at least 15 committed subjects").'
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
    lines += ["", total_note, "", scope_note]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
