"""Unit tests for report.py's H1-H3 statistics (Working Brief §6)."""

from __future__ import annotations

import json

from seqrefactor.model import MetricDelta, QualityWeights, RunReport, StepRecord, Verdict
from seqrefactor.report import (
    Reporter,
    auc_quality_trajectory,
    hypothesis_tests,
    normalised_auc,
    quality_score,
    weighted_auc_quality_trajectory,
    weighted_quality_trajectory,
)


def _run(
    subject: str,
    strategy: str,
    generator: str,
    n_accepted: int,
    n_cascades: int,
    metric: MetricDelta | None = None,
) -> RunReport:
    steps = []
    for i in range(max(n_accepted, n_cascades)):
        steps.append(
            StepRecord(
                index=i,
                smell=f"s{i}",
                verdict=Verdict(smell=f"s{i}", accepted=i < n_accepted, rationale="test"),
                cascading_violation=i < n_cascades,
                metric=metric or MetricDelta(),
            )
        )
    return RunReport(subject=subject, strategy=strategy, generator=generator, steps=steps)


def _five_subject_runs(strategy_a: str, strategy_b: str, a_casc: int, b_casc: int) -> list[RunReport]:
    runs = []
    for i in range(5):
        runs.append(_run(f"subj{i}", strategy_a, "baseline", n_accepted=5, n_cascades=a_casc))
        runs.append(_run(f"subj{i}", strategy_b, "baseline", n_accepted=5, n_cascades=b_casc))
    return runs


def test_h1_detects_fewer_cascading_violations_for_seqrefactor() -> None:
    runs = _five_subject_runs("seqrefactor", "unordered", a_casc=0, b_casc=3)

    results = hypothesis_tests(runs)

    h1 = results["H1_fewer_cascading_violations_vs_unordered"]
    assert h1.n == 5
    assert h1.supported is True


def test_h1_reports_insufficient_data_with_too_few_paired_subjects() -> None:
    runs = _run("only_subject", "seqrefactor", "baseline", 5, 0), _run(
        "only_subject", "unordered", "baseline", 5, 3
    )

    results = hypothesis_tests(list(runs))

    h1 = results["H1_fewer_cascading_violations_vs_unordered"]
    assert h1.n == 1
    assert h1.supported is None


def test_h2_uses_net_smell_resolution_against_unordered_and_topo_only() -> None:
    runs = []
    for i in range(5):
        runs.append(_run(f"subj{i}", "seqrefactor", "baseline", n_accepted=5, n_cascades=0))
        runs.append(_run(f"subj{i}", "unordered", "baseline", n_accepted=1, n_cascades=0))
        runs.append(_run(f"subj{i}", "topo_only", "baseline", n_accepted=2, n_cascades=0))

    results = hypothesis_tests(runs)

    assert results["H2_higher_nsr_vs_unordered"].supported is True
    assert results["H2_higher_nsr_vs_topo_only"].supported is True


def test_reporter_ablation_output_is_json_serializable() -> None:
    """Regression test: Reporter.ablation()'s dict is written verbatim to summary.json
    by the CLI's `run` command via plain json.dumps -- it must be JSON-safe on its own,
    not leak PairedTestResult dataclass instances (caught for real running the pipeline
    against datasets/opensource/json_java_v1, see PROVENANCE.md)."""
    runs = [_run("subj", "seqrefactor", "baseline", n_accepted=3, n_cascades=0)]

    summary = Reporter().ablation(runs)

    json.dumps(summary)  # must not raise TypeError


def test_auc_quality_trajectory_is_nonnegative_and_monotone_with_more_accepts() -> None:
    fewer = _run("s", "seqrefactor", "baseline", n_accepted=1, n_cascades=0)
    more = _run("s", "seqrefactor", "baseline", n_accepted=5, n_cascades=0)

    assert auc_quality_trajectory(fewer) >= 0
    assert auc_quality_trajectory(more) > auc_quality_trajectory(fewer)


def test_quality_score_is_weighted_sum_over_five_families() -> None:
    metric = MetricDelta(cohesion=1.0, coupling=2.0, complexity=3.0, readability=4.0, architecture=5.0)

    equal = quality_score(metric, QualityWeights())
    assert equal == (1.0 + 2.0 + 3.0 + 4.0 + 5.0) * 0.2

    coupling_only = quality_score(
        metric, QualityWeights(cohesion=0, coupling=1, complexity=0, readability=0, architecture=0)
    )
    assert coupling_only == 2.0


def test_weighted_quality_trajectory_only_accumulates_on_accepted_steps() -> None:
    metric = MetricDelta(cohesion=1.0, coupling=1.0, complexity=1.0, readability=1.0, architecture=1.0)
    run = _run("s", "seqrefactor", "baseline", n_accepted=2, n_cascades=0, metric=metric)
    # 4 steps total (max(n_accepted, n_cascades) with n_cascades=0 -> range(2)), so build
    # explicitly to get a rejected step in the middle and confirm it contributes zero.
    steps = [
        StepRecord(
            index=0, smell="a", verdict=Verdict(smell="a", accepted=True, rationale="ok"), metric=metric
        ),
        StepRecord(
            index=1, smell="b", verdict=Verdict(smell="b", accepted=False, rationale="no"), metric=metric
        ),
        StepRecord(
            index=2, smell="c", verdict=Verdict(smell="c", accepted=True, rationale="ok"), metric=metric
        ),
    ]
    run = RunReport(subject="s", strategy="seqrefactor", generator="baseline", steps=steps)

    trajectory = weighted_quality_trajectory(run, QualityWeights())

    assert trajectory == [1.0, 1.0, 2.0]  # step 1 (rejected) contributes nothing


def test_normalised_auc_divides_by_step_count() -> None:
    trajectory = [1.0, 2.0, 3.0, 4.0]
    assert normalised_auc(trajectory) == 2.5  # (1+2+3+4)/4
    assert normalised_auc([]) == 0.0


def test_normalised_auc_narrows_but_does_not_erase_the_step_count_gap() -> None:
    """E2.2's actual concern, checked precisely rather than assumed: the brief's own
    formula (``AUC_norm = (1/T) * sum of the CUMULATIVE trajectory``) divides the raw
    trapezoid area by T, which narrows the gap between a short and a long run at
    identical per-step quality, but does not fully erase it -- a cumulative ramp's mean
    still grows with T even after dividing by T once (mean of 1..T is (T+1)/2, not
    constant). Hand-computed for T=2 vs T=8 at a constant per-step delta of 1.0:
    raw ratio 31.5/1.5 = 21x, normalised ratio 4.5/1.5 = 3x -- narrower, not equal. A
    unit test asserting full equality here would be asserting something false about
    this formula, not a property it actually has; if a fully step-count-invariant
    score is wanted later, that is a different formula (e.g. dividing each step's OWN
    contribution by T before accumulating, not normalising the cumulative curve after
    the fact), not a bug in this implementation of the brief's literal formula."""
    metric = MetricDelta(cohesion=1.0, coupling=0, complexity=0, readability=0, architecture=0)
    weights = QualityWeights(cohesion=1, coupling=0, complexity=0, readability=0, architecture=0)
    short_run = _run("s", "seqrefactor", "baseline", n_accepted=2, n_cascades=0, metric=metric)
    long_run = _run("s", "seqrefactor", "baseline", n_accepted=8, n_cascades=0, metric=metric)

    short_raw = weighted_auc_quality_trajectory(short_run, weights)
    long_raw = weighted_auc_quality_trajectory(long_run, weights)
    assert (short_raw, long_raw) == (1.5, 31.5)

    short_norm = normalised_auc(weighted_quality_trajectory(short_run, weights))
    long_norm = normalised_auc(weighted_quality_trajectory(long_run, weights))
    assert (short_norm, long_norm) == (1.5, 4.5)

    raw_ratio = long_raw / short_raw
    norm_ratio = long_norm / short_norm
    assert norm_ratio < raw_ratio  # narrower...
    assert norm_ratio > 1.0  # ...but a real gap remains for this formula
