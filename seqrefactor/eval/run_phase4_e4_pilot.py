"""Driver for Working Brief Phase 4, Task E4 -- REDUCED PILOT, not the full
brief-specified scope (8 strategies x 28 subjects x N=3), pending real
cost/timing data from this smaller run before committing to the full matrix
(user's explicit choice, see the conversation this was built in).

Pilot scope: 3 strategies (seqrefactor, unordered, topo_only -- the exact
three ``report.hypothesis_tests`` pairs for H1/H3, so this pilot can compute
real H1/H3-under-LLM numbers, not just generation-success-rate) x 4
representative subjects x N=3 repetitions x max_steps=5 (reduced from the
corpus default of 10 to bound cost/time for a first pilot).

REPETITIONS AND SEEDS (a real correctness issue caught before spending any
money, not a detail to skip): ``generate/llm.py`` uses ``temperature=0.0``
and caches by a content hash that includes the seed. Running N "repetitions"
at the SAME seed would replay the SAME cache entry (or, on a fresh call,
produce a near-identical low-temperature sample) every time -- capturing
nothing about non-determinism. Each repetition here therefore uses a
DISTINCT base seed (``cfg.seed`` offset by repetition index x 1000, so a
single run's own per-step seeds via ``cfg.seed + step_index`` never collide
across repetitions), and each repetition's own cache is fully committed and
replayable on its own (NFR-2), so the pilot's reproducibility story is
"replay these N specific seeded runs exactly," not "replay one run and
assume the others matched."

Model: set via the SEQREFACTOR_LLM_MODEL environment variable before running
this script (not hard-coded here), so the model used is whatever the
invoking command set it to, disclosed exactly by whatever it printed.

**Never point this at datasets/synthetic/ directly** -- the orchestrator
mutates its target module in place, and requires OPENAI_API_KEY to be set.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from seqrefactor.model import Config, RunReport
from seqrefactor.orchestrator import Orchestrator
from seqrefactor.report import Reporter

PILOT_STRATEGIES = ["seqrefactor", "unordered", "topo_only"]
PILOT_SUBJECTS = ["pilot_checkout_v1", "synth_small_medium", "synth_medium_medium", "conflict_pair_a"]
PILOT_REPETITIONS = 3
PILOT_MAX_STEPS = 5
SEED_OFFSET_PER_REPETITION = 1000


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch-corpus", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("evaluation") / "llm_pilot")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set; E4 needs a real LLM generator.")
    model = os.environ.get("SEQREFACTOR_LLM_MODEL", "<unset, generate/llm.py's own default>")
    print(f"E4 PILOT: model={model}, strategies={PILOT_STRATEGIES}, subjects={PILOT_SUBJECTS}, "
          f"repetitions={PILOT_REPETITIONS}, max_steps={PILOT_MAX_STEPS}")

    subject_paths = [args.scratch_corpus / name for name in PILOT_SUBJECTS]
    missing = [p for p in subject_paths if not p.is_dir()]
    if missing:
        raise SystemExit(f"missing scratch subject(s): {missing}")

    orchestrator = Orchestrator()
    all_runs: list[RunReport] = []
    start = time.perf_counter()

    for repetition in range(PILOT_REPETITIONS):
        cfg = Config(
            subjects_glob=str(args.scratch_corpus / "*"),
            generators=["llm"],
            coverage_min=0.0,
            seed=20260101 + repetition * SEED_OFFSET_PER_REPETITION,
            max_steps=PILOT_MAX_STEPS,
        )
        for path in subject_paths:
            for strategy in PILOT_STRATEGIES:
                run_start = time.perf_counter()
                report = orchestrator.run_one(path, cfg, strategy=strategy, generator="llm")
                report = report.model_copy(update={"repetition": repetition})
                run_elapsed = time.perf_counter() - run_start
                all_runs.append(report)
                print(
                    f"  rep={repetition} seed={cfg.seed} subject={report.subject} "
                    f"strategy={report.strategy}: steps={len(report.steps)} "
                    f"gsr={report.generation_success_rate:.2f} nsr={report.net_smell_resolution} "
                    f"cascades={report.cascading_violations} ({run_elapsed:.1f}s)"
                )

    elapsed = time.perf_counter() - start
    print(f"E4 PILOT: {len(all_runs)} runs complete in {elapsed / 60:.1f} minutes")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    # Indexed filenames disambiguate reruns of the same (subject, strategy) across
    # repetitions -- the repetition's seed itself isn't stored on RunReport, so the
    # index is what ties a file back to this run's own stdout log above.
    for idx, report in enumerate(all_runs):
        (args.out_dir / f"run_{idx:03d}_{report.subject}_{report.strategy}.json").write_text(
            report.model_dump_json(indent=2), encoding="utf-8"
        )

    summary = Reporter().ablation(all_runs)
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"E4 PILOT: wrote {len(all_runs)} RunReports + summary.json to {args.out_dir}")

    h = summary["hypothesis_tests"]
    for name in ("H1_fewer_cascading_violations_vs_unordered", "H3_higher_auc_vs_topo_only"):
        r = h[name]
        print(f"  {name}: n={r['n']} p={r['p_value']} supported={r['supported']}")

    print("done")


if __name__ == "__main__":
    main()
