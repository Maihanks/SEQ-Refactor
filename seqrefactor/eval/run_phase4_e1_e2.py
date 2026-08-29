"""Driver for Working Brief Phase 4, Tasks E1 and E2. Not imported anywhere else;
run directly (``uv run python -m seqrefactor.eval.run_phase4_e1_e2``) against a
scratch copy of the corpus.

E1 (impact-score ablation) requires five full orchestrator sweeps (the impact
weights change which vertex gets ordered first, so the actual sequence of
transformations differs per configuration). E2's weight-sensitivity half
(2.1) reuses E1's A5 (default-weight) runs directly rather than re-running
anything -- see ``quality_sensitivity.py``'s module docstring for why that
is correct, not a shortcut.

**Never point this at datasets/synthetic/ directly** -- the orchestrator
mutates its target module in place. This script requires the corpus to
already be copied to a scratch location and takes that path as an argument.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from seqrefactor.eval.ablation_impact import run_impact_ablation, table_impact_ablation
from seqrefactor.eval.quality_sensitivity import table_quality_sensitivity
from seqrefactor.eval import tables as eval_tables
from seqrefactor.model import Config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scratch-corpus",
        required=True,
        type=Path,
        help="Path to a scratch copy of datasets/synthetic/ (subdirectories per subject).",
    )
    parser.add_argument("--out-dir", type=Path, default=Path("evaluation"))
    parser.add_argument(
        "--raw-out",
        type=Path,
        default=Path("evaluation") / "phase4_e1_raw_runs.json",
        help="Where to dump every raw RunReport (E1's runs, reused by E2) for audit.",
    )
    args = parser.parse_args()

    # Filter by manifest.yaml presence, matching seqrefactor.datasets.list_subjects's own
    # filter -- datasets/synthetic/ also holds non-subject directories (e.g. example_run/,
    # a committed reference run's raw output) that a bare is_dir() would wrongly include.
    subject_paths = sorted(
        p for p in args.scratch_corpus.iterdir() if p.is_dir() and (p / "manifest.yaml").is_file()
    )
    if not subject_paths:
        print(f"no subject directories found under {args.scratch_corpus}", file=sys.stderr)
        raise SystemExit(1)
    print(f"E1: {len(subject_paths)} subjects x 5 impact-weight configurations x 2 strategies")

    base_cfg = Config(
        subjects_glob=str(args.scratch_corpus / "*"),
        generators=["baseline"],
        coverage_min=0.0,
        seed=20260101,
        max_steps=10,
    )

    start = time.perf_counter()
    runs_by_configuration = run_impact_ablation(base_cfg, subject_paths, generator="baseline")
    elapsed = time.perf_counter() - start
    print(f"E1: all configurations complete in {elapsed / 60:.1f} minutes")

    args.raw_out.parent.mkdir(parents=True, exist_ok=True)
    args.raw_out.write_text(
        json.dumps(
            {
                name: [json.loads(r.model_dump_json()) for r in runs]
                for name, runs in runs_by_configuration.items()
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"E1: raw runs written to {args.raw_out}")

    e1_rows = table_impact_ablation(runs_by_configuration)
    eval_tables.table_impact_ablation(e1_rows, out_dir=args.out_dir)
    print(f"E1: table_impact_ablation.csv written to {args.out_dir}")
    for row in e1_rows:
        print(f"  {row['configuration']}: n={row['n']} p={row['p_value']} supported={row['supported']}")

    default_runs = runs_by_configuration["A5_all_three_default"]
    e2_rows = table_quality_sensitivity(default_runs)
    eval_tables.table_quality_sensitivity(e2_rows, out_dir=args.out_dir)
    print(f"E2: table_quality_sensitivity.csv written to {args.out_dir}")
    for row in e2_rows:
        print(
            f"  {row['weight_vector']}/{row['score_mode']}: "
            f"n={row['n']} p={row['p_value']} supported={row['supported']}"
        )

    print("done")


if __name__ == "__main__":
    main()
