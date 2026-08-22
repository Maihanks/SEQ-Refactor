"""Unit tests for report.py's H1-H3 statistics (Working Brief §6)."""

from __future__ import annotations

from seqrefactor.model import RunReport, StepRecord, Verdict
from seqrefactor.report import auc_quality_trajectory, hypothesis_tests


def _run(subject: str, strategy: str, generator: str, n_accepted: int, n_cascades: int) -> RunReport:
    steps = []
    for i in range(max(n_accepted, n_cascades)):
        steps.append(
            StepRecord(
                index=i,
                smell=f"s{i}",
                verdict=Verdict(smell=f"s{i}", accepted=i < n_accepted, rationale="test"),
                cascading_violation=i < n_cascades,
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


def test_auc_quality_trajectory_is_nonnegative_and_monotone_with_more_accepts() -> None:
    fewer = _run("s", "seqrefactor", "baseline", n_accepted=1, n_cascades=0)
    more = _run("s", "seqrefactor", "baseline", n_accepted=5, n_cascades=0)

    assert auc_quality_trajectory(fewer) >= 0
    assert auc_quality_trajectory(more) > auc_quality_trajectory(fewer)
