"""E1: impact-score ablation (Working Brief Phase 4, Task E1).

Question: is H3's early-quality advantage (SEQ-REFACTOR vs. topology-only,
area under the cumulative-quality-vs-step curve) a property of
impact-forward scheduling in general, or an artefact of the paper's default
impact weighting (alpha=0.4, beta=0.4, gamma=0.2)?

Method: re-run the seqrefactor-vs-topo_only H3 comparison across the full
corpus under five impact weightings (Impact(v) = alpha*coupling +
beta*complexity + gamma*co-occurrence, Eq. 1) --

  A1 coupling only    (alpha=1, beta=0,   gamma=0)
  A2 complexity only  (alpha=0, beta=1,   gamma=0)
  A3 co-occurrence only (alpha=0, beta=0, gamma=1)
  A4 coupling+complexity, equal (alpha=0.5, beta=0.5, gamma=0)
  A5 all three, the paper's default (alpha=0.4, beta=0.4, gamma=0.2)

Every configuration is run for real through the orchestrator (the impact
weights change which vertex gets selected at each step, so the actual
sequence of transformations differs per configuration -- there is no way to
compute this from a single canonical run the way E2.1's quality-weight
sensitivity can). Uses the deterministic baseline generator throughout, for
the same reason the main ablation and the RQ4 weight sweep do: isolating the
ordering effect from generator variance, and keeping the study free and
exactly reproducible.

One rule that cannot be broken (brief's own wording): report whatever comes
out. If H3 does not hold under some weighting, that is the finding.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from seqrefactor.eval.stats import PairedTestResult, paired_test
from seqrefactor.model import Config, ImpactWeights, RunReport
from seqrefactor.orchestrator import Orchestrator
from seqrefactor.report import _paired_values, auc_quality_trajectory

IMPACT_ABLATION_CONFIGURATIONS: dict[str, ImpactWeights] = {
    "A1_coupling_only": ImpactWeights(alpha=1.0, beta=0.0, gamma=0.0),
    "A2_complexity_only": ImpactWeights(alpha=0.0, beta=1.0, gamma=0.0),
    "A3_cooccurrence_only": ImpactWeights(alpha=0.0, beta=0.0, gamma=1.0),
    "A4_coupling_complexity_equal": ImpactWeights(alpha=0.5, beta=0.5, gamma=0.0),
    "A5_all_three_default": ImpactWeights(alpha=0.4, beta=0.4, gamma=0.2),
}


def run_impact_ablation(
    base_cfg: Config,
    subject_paths: list[Path],
    generator: str = "baseline",
    configurations: dict[str, ImpactWeights] | None = None,
) -> dict[str, list[RunReport]]:
    """Run "seqrefactor" and "topo_only" over every subject at every impact-weight
    configuration. Returns the raw RunReports keyed by configuration name (not just
    the H3 summary) so a caller can recompute other measures from the same runs
    without re-executing the pipeline -- see ``table_impact_ablation`` below for the
    H3-specific reduction, and ``seqrefactor.eval.quality_sensitivity`` for reuse of
    the A5 (default-weight) subset.
    """
    configurations = configurations or IMPACT_ABLATION_CONFIGURATIONS
    orchestrator = Orchestrator()
    runs_by_configuration: dict[str, list[RunReport]] = {}

    for config_name, weights in configurations.items():
        cfg = base_cfg.model_copy(update={"impact_weights": weights})
        runs: list[RunReport] = []
        for path in subject_paths:
            for strategy in ("seqrefactor", "topo_only"):
                runs.append(orchestrator.run_one(path, cfg, strategy=strategy, generator=generator))
        runs_by_configuration[config_name] = runs

    return runs_by_configuration


def table_impact_ablation(runs_by_configuration: dict[str, list[RunReport]]) -> list[dict]:
    """H3 (paired seqrefactor-vs-topo_only AUC test, ``report.py``'s own
    ``eval.stats.paired_test`` machinery) computed independently per impact-weight
    configuration -- one row per configuration, exactly the deliverable
    ``evaluation/table_impact_ablation.csv`` specifies."""
    rows: list[dict] = []
    for config_name, runs in runs_by_configuration.items():
        weights = IMPACT_ABLATION_CONFIGURATIONS.get(config_name)
        seq_auc, topo_auc = _paired_values(runs, "seqrefactor", "topo_only", auc_quality_trajectory)
        result: PairedTestResult = paired_test(seq_auc, topo_auc, direction="greater")
        row = {
            "configuration": config_name,
            "alpha": weights.alpha if weights else None,
            "beta": weights.beta if weights else None,
            "gamma": weights.gamma if weights else None,
            **asdict(result),
        }
        rows.append(row)
    return rows
