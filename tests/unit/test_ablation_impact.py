"""Unit tests for the E1 impact-score ablation's H3 reduction (Working Brief
Phase 4). Only ``table_impact_ablation`` (a pure reduction over already-built
RunReports) is unit-tested here -- ``run_impact_ablation`` itself is a thin
wrapper over the already-tested ``Orchestrator.run_one`` and needs the real
sidecar, exercised by the actual E1 study run, not a fast unit test.
"""

from __future__ import annotations

from seqrefactor.eval.ablation_impact import IMPACT_ABLATION_CONFIGURATIONS, table_impact_ablation
from seqrefactor.model import RunReport, StepRecord, Verdict


def _run(subject: str, strategy: str, n_accepted: int) -> RunReport:
    steps = [
        StepRecord(
            index=i, smell=f"s{i}", verdict=Verdict(smell=f"s{i}", accepted=i < n_accepted, rationale="t")
        )
        for i in range(5)
    ]
    return RunReport(subject=subject, strategy=strategy, generator="baseline", steps=steps)


def test_table_impact_ablation_has_one_row_per_configuration() -> None:
    runs_by_configuration = {
        name: [
            run
            for i in range(5)
            for run in (
                _run(f"subj{i}", "seqrefactor", n_accepted=5),
                _run(f"subj{i}", "topo_only", n_accepted=2),
            )
        ]
        for name in IMPACT_ABLATION_CONFIGURATIONS
    }

    rows = table_impact_ablation(runs_by_configuration)

    assert len(rows) == len(IMPACT_ABLATION_CONFIGURATIONS)
    configs_seen = {r["configuration"] for r in rows}
    assert configs_seen == set(IMPACT_ABLATION_CONFIGURATIONS)
    for row in rows:
        assert row["n"] == 5
        assert row["supported"] is True  # seqrefactor strictly outperforms in every pair here


def test_table_impact_ablation_reports_unsupported_when_advantage_disappears() -> None:
    """The brief's own acceptance check: an ablation that shows the advantage
    disappearing under some weighting must say so, not hide it."""
    runs_by_configuration = {
        "A1_coupling_only": [
            run
            for i in range(5)
            for run in (
                _run(f"subj{i}", "seqrefactor", n_accepted=2),
                _run(f"subj{i}", "topo_only", n_accepted=2),  # identical -> no advantage
            )
        ]
    }

    rows = table_impact_ablation(runs_by_configuration)

    assert len(rows) == 1
    assert rows[0]["supported"] is None  # every paired difference is exactly zero (degenerate)


def test_impact_ablation_weight_configurations_match_brief_a1_to_a5() -> None:
    """Regression test pinning the exact five weightings the brief specifies (§1),
    so a future edit cannot silently drift from A1-A5's definitions."""
    configs = IMPACT_ABLATION_CONFIGURATIONS
    assert (configs["A1_coupling_only"].alpha, configs["A1_coupling_only"].beta, configs["A1_coupling_only"].gamma) == (1.0, 0.0, 0.0)
    assert (configs["A2_complexity_only"].alpha, configs["A2_complexity_only"].beta, configs["A2_complexity_only"].gamma) == (0.0, 1.0, 0.0)
    assert (configs["A3_cooccurrence_only"].alpha, configs["A3_cooccurrence_only"].beta, configs["A3_cooccurrence_only"].gamma) == (0.0, 0.0, 1.0)
    assert (configs["A4_coupling_complexity_equal"].alpha, configs["A4_coupling_complexity_equal"].beta, configs["A4_coupling_complexity_equal"].gamma) == (0.5, 0.5, 0.0)
    assert (configs["A5_all_three_default"].alpha, configs["A5_all_three_default"].beta, configs["A5_all_three_default"].gamma) == (0.4, 0.4, 0.2)
