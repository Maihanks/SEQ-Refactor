"""Ablation tables and per-step trajectory (Software Specification §5.9, §8.3).

Reads only the derived, computed-property fields on RunReport (net smell
resolution, cascading violations, ordering validity, escalation rate) --
never independently recomputes or overrides them -- so a reported number is
always the same one that Section 6's data model contract guarantees is
re-derivable from the persisted per-step artefacts.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

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


class Reporter:
    """Implements the ``Reporter`` contract (§5.9): ``ablation(runs) -> Report``."""

    def ablation(self, runs: list[RunReport]) -> dict:
        return {
            "cells": ablation_table(runs),
            "by_strategy": aggregate_by_strategy(runs),
        }
