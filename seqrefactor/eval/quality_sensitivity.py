"""E2: quality-score sensitivity and AUC normalisation (Working Brief Phase 4, Task E2).

Question: H3 (SEQ-REFACTOR vs. topology-only, early cumulative quality gain)
currently measures "quality" as cumulative accepted-step count
(``report.quality_trajectory``). Two risks the brief names: (2.1) the
conclusion may be an artefact of that particular notion of quality rather
than a real weighted metric improvement, and (2.2) summing over steps can
favour subjects that simply ran more steps.

Method: this module does NOT re-run the orchestrator. Unlike E1 (where the
impact weights change which vertex gets selected at each step, so a fresh
run is unavoidable), a quality-weight vector only changes how an
ALREADY-RECORDED step's MetricDelta (``StepRecord.metric``, Working Brief
Phase 4's own data-model addition) is reduced to a scalar after the fact --
so the SAME seqrefactor-vs-topo_only runs collected for E1's A5
(default-impact-weight) configuration are reused directly. Re-running would
not change the underlying transformations, patches, or verdicts, only waste
real sidecar compile/test cycles recomputing numbers already on disk.

2.1 Weight sensitivity: H3 under the existing accepted-count measure
    ("current"), equal metric weights (1/5 each), and two further vectors
    each emphasising a different pair of families.
2.2 AUC normalisation: every one of the above is reported under both the
    existing summed (trapezoid) score and the step-count-normalised
    ``report.normalised_auc``.

One rule that cannot be broken (brief's own wording): report whatever comes
out. If the conclusion flips under some weighting or under normalisation,
that is the finding, not something to paper over.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict

from seqrefactor.eval.stats import PairedTestResult, paired_test
from seqrefactor.model import QualityWeights, RunReport
from seqrefactor.report import (
    _paired_values,
    auc_quality_trajectory,
    normalised_auc,
    quality_trajectory,
    weighted_auc_quality_trajectory,
    weighted_quality_trajectory,
)

QUALITY_WEIGHT_VECTORS: dict[str, QualityWeights] = {
    "equal": QualityWeights(
        cohesion=0.2, coupling=0.2, complexity=0.2, readability=0.2, architecture=0.2
    ),
    "coupling_complexity_heavy": QualityWeights(
        cohesion=0.15, coupling=0.35, complexity=0.35, readability=0.075, architecture=0.075
    ),
    "readability_architecture_heavy": QualityWeights(
        cohesion=0.075, coupling=0.075, complexity=0.15, readability=0.35, architecture=0.35
    ),
}


def table_quality_sensitivity(runs: list[RunReport]) -> list[dict]:
    """H3 under every (quality-weight vector, score mode) combination -- the
    deliverable ``evaluation/table_quality_sensitivity.csv`` specifies. ``runs`` should
    be the seqrefactor + topo_only RunReports from a single impact-weight configuration
    (the default/A5 one, to match H3's existing framing) across the full corpus."""
    rows: list[dict] = []

    # "current": the pre-existing, un-weighted accepted-count measure (report.py's
    # original quality_trajectory), included as the reference point everything else
    # is being checked against, not just the new weighted variants.
    for mode, trajectory_fn in (
        ("summed", auc_quality_trajectory),
        ("normalised", lambda r: normalised_auc(quality_trajectory(r))),
    ):
        seq_vals, topo_vals = _paired_values(runs, "seqrefactor", "topo_only", trajectory_fn)
        result: PairedTestResult = paired_test(seq_vals, topo_vals, direction="greater")
        rows.append({"weight_vector": "current_accepted_count", "score_mode": mode, **asdict(result)})

    for vector_name, weights in QUALITY_WEIGHT_VECTORS.items():
        modes: dict[str, Callable[[RunReport], float]] = {
            "summed": lambda r, w=weights: weighted_auc_quality_trajectory(r, w),
            "normalised": lambda r, w=weights: normalised_auc(weighted_quality_trajectory(r, w)),
        }
        for mode, trajectory_fn in modes.items():
            seq_vals, topo_vals = _paired_values(runs, "seqrefactor", "topo_only", trajectory_fn)
            result = paired_test(seq_vals, topo_vals, direction="greater")
            rows.append({"weight_vector": vector_name, "score_mode": mode, **asdict(result)})

    return rows
