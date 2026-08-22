"""Ablation tables and per-step trajectory (Software Specification §5.9, §8.3).

Reads only the derived, computed-property fields on RunReport (net smell
resolution, cascading violations, ordering validity, escalation rate) --
never independently recomputes or overrides them -- so a reported number is
always the same one that Section 6's data model contract guarantees is
re-derivable from the persisted per-step artefacts.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from statistics import mean

import numpy as np

from seqrefactor.eval.stats import PairedTestResult, paired_test
from seqrefactor.model import RunReport


class AblationCell(dict):
    """A (subject, strategy, generator) row of the ablation table."""


def ablation_table(runs: list[RunReport]) -> list[AblationCell]:
    return [
        AblationCell(
            subject=r.subject,
            strategy=r.strategy,
            generator=r.generator,
            net_smell_resolution=r.net_smell_resolution,
            cascading_violations=r.cascading_violations,
            ordering_validity=r.ordering_validity,
            escalation_rate=r.escalation_rate,
            steps=len(r.steps),
        )
        for r in runs
    ]


def aggregate_by_strategy(runs: list[RunReport]) -> dict[str, dict[str, float]]:
    """Mean of each dependent measure across subjects, grouped by ordering strategy
    (§8.3: "Aggregate across subjects with non-parametric paired tests and report
    effect sizes" -- this returns the descriptive means the paired tests are run
    over; statistical testing itself is out of scope for this facade)."""
    by_strategy: dict[str, list[RunReport]] = defaultdict(list)
    for r in runs:
        by_strategy[r.strategy].append(r)

    result: dict[str, dict[str, float]] = {}
    for strategy, group in by_strategy.items():
        result[strategy] = {
            "net_smell_resolution": mean(r.net_smell_resolution for r in group),
            "cascading_violations": mean(r.cascading_violations for r in group),
            "ordering_validity": mean(r.ordering_validity for r in group),
            "escalation_rate": mean(r.escalation_rate for r in group),
            "n_subjects": len(group),
        }
    return result


def quality_trajectory(run: RunReport) -> list[float]:
    """Cumulative accepted-step count over time, the raw series behind the
    "area under the quality-versus-step curve" measure of H3 (§Research
    Questions and Hypotheses). Callers needing an actual metric-quality curve
    (rather than acceptance count) should sum StepRecord.verdict-linked
    MetricDelta values from the persisted per-step artefacts instead."""
    cumulative = 0.0
    trajectory = []
    for step in run.steps:
        if step.verdict.accepted:
            cumulative += 1.0
        trajectory.append(cumulative)
    return trajectory


def auc_quality_trajectory(run: RunReport) -> float:
    """Area under the cumulative-quality-vs-step curve (H3), via the trapezoid
    rule over ``quality_trajectory``'s cumulative accepted-step series."""
    trajectory = quality_trajectory(run)
    return float(np.trapezoid(trajectory)) if trajectory else 0.0


def _paired_values(
    runs: list[RunReport],
    strategy_a: str,
    strategy_b: str,
    metric: Callable[[RunReport], float],
) -> tuple[list[float], list[float]]:
    """Pair runs of ``strategy_a`` and ``strategy_b`` sharing the same
    (subject, generator) cell -- the paired design H1-H3's statistics require
    (Software Specification §8.3's ordering-strategy independent variable,
    generator held fixed as a control)."""
    by_cell: dict[tuple[str, str], dict[str, RunReport]] = defaultdict(dict)
    for r in runs:
        by_cell[(r.subject, r.generator)][r.strategy] = r

    a_vals: list[float] = []
    b_vals: list[float] = []
    for strategies in by_cell.values():
        if strategy_a in strategies and strategy_b in strategies:
            a_vals.append(metric(strategies[strategy_a]))
            b_vals.append(metric(strategies[strategy_b]))
    return a_vals, b_vals


def hypothesis_tests(runs: list[RunReport]) -> dict[str, PairedTestResult]:
    """H1-H3 (paper §VII-A), each a paired non-parametric test over matching
    (subject, generator) cells via ``eval.stats.paired_test`` (Working Brief
    §6: "non-parametric paired tests with effect sizes and 95 percent
    confidence intervals"). RQ4's weight-sensitivity sweep is a separate
    concern (``eval/weight_sweep.py``), since it varies impact weights rather
    than comparing ordering strategies."""
    results: dict[str, PairedTestResult] = {}

    # H1: SEQ-REFACTOR yields significantly fewer cascading violations than unordered.
    unordered_casc, seq_casc = _paired_values(
        runs, "unordered", "seqrefactor", lambda r: r.cascading_violations
    )
    results["H1_fewer_cascading_violations_vs_unordered"] = paired_test(
        unordered_casc, seq_casc, direction="greater"
    )

    # H2: SEQ-REFACTOR yields higher net smell resolution than both unordered and topo-only.
    seq_nsr_u, unordered_nsr = _paired_values(
        runs, "seqrefactor", "unordered", lambda r: r.net_smell_resolution
    )
    results["H2_higher_nsr_vs_unordered"] = paired_test(seq_nsr_u, unordered_nsr, direction="greater")

    seq_nsr_t, topo_nsr = _paired_values(
        runs, "seqrefactor", "topo_only", lambda r: r.net_smell_resolution
    )
    results["H2_higher_nsr_vs_topo_only"] = paired_test(seq_nsr_t, topo_nsr, direction="greater")

    # H3: impact-forward placement yields higher early cumulative quality gain
    # (area under the quality-vs-step curve) than topology-only ordering.
    seq_auc, topo_auc = _paired_values(runs, "seqrefactor", "topo_only", auc_quality_trajectory)
    results["H3_higher_auc_vs_topo_only"] = paired_test(seq_auc, topo_auc, direction="greater")

    return results


class Reporter:
    """Implements the ``Reporter`` contract (§5.9): ``ablation(runs) -> Report``."""

    def ablation(self, runs: list[RunReport]) -> dict:
        return {
            "cells": ablation_table(runs),
            "by_strategy": aggregate_by_strategy(runs),
            "hypothesis_tests": hypothesis_tests(runs),
        }
