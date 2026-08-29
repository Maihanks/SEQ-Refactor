"""Driver for Working Brief Phase 4, Task E3: run the new ouni_nsga2 strategy
across the full corpus and merge its rows into the existing Table II ablation
(the other seven strategies already have committed results; this only adds
the new one rather than expensively re-running everything).

**Never point this at datasets/synthetic/ directly** -- the orchestrator
mutates its target module in place.
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from seqrefactor.eval import tables as eval_tables
from seqrefactor.model import Config
from seqrefactor.orchestrator import Orchestrator
from seqrefactor.report import ablation_table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch-corpus", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("evaluation"))
    parser.add_argument(
        "--existing-csv",
        type=Path,
        default=Path("evaluation") / "table2_ablation.csv",
        help="The already-committed Table II to merge ouni_nsga2's rows into.",
    )
    args = parser.parse_args()

    subject_paths = sorted(
        p for p in args.scratch_corpus.iterdir() if p.is_dir() and (p / "manifest.yaml").is_file()
    )
    print(f"E3: {len(subject_paths)} subjects, ouni_nsga2 strategy only")

    cfg = Config(
        subjects_glob=str(args.scratch_corpus / "*"),
        strategies=["ouni_nsga2"],
        generators=["baseline"],
        coverage_min=0.0,
        seed=20260101,
        max_steps=10,
    )

    orchestrator = Orchestrator()
    start = time.perf_counter()
    new_runs = orchestrator.run_matrix(cfg, subject_paths)
    elapsed = time.perf_counter() - start
    print(f"E3: ouni_nsga2 complete across {len(subject_paths)} subjects in {elapsed / 60:.1f} minutes")

    new_rows = [dict(cell) for cell in ablation_table(new_runs)]

    existing_rows: list[dict] = []
    if args.existing_csv.is_file():
        with args.existing_csv.open("r", newline="", encoding="utf-8") as fh:
            existing_rows = list(csv.DictReader(fh))
        # Cast numeric columns back from CSV's strings so re-emission formats them
        # the same way ablation_table's own output does, not as quoted strings.
        for row in existing_rows:
            for key in ("net_smell_resolution", "cascading_violations", "steps"):
                row[key] = int(row[key])
            for key in ("ordering_validity", "escalation_rate"):
                row[key] = float(row[key])

    combined = [r for r in existing_rows if r["strategy"] != "ouni_nsga2"] + new_rows
    combined.sort(key=lambda r: (r["subject"], r["strategy"]))

    eval_tables.emit_table(
        combined,
        "table2_ablation",
        "SEQ-REFACTOR ablation (RQ1-RQ4)",
        "tab:ablation",
        out_dir=args.out_dir,
    )
    print(f"E3: table2_ablation.csv re-emitted with {len(combined)} rows ({len(new_rows)} new) to {args.out_dir}")
    print("done")


if __name__ == "__main__":
    main()
