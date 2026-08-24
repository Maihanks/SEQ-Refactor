"""Unit tests for eval/tables.py (Working Brief §8)."""

from __future__ import annotations

from seqrefactor.eval.detector_quality import DetectorQualityResult
from seqrefactor.eval.random_study import RandomBaselineResult
from seqrefactor.eval.tables import (
    summary_md,
    table2_ablation,
    table3_depmass,
    table4_efficiency,
    table5_detector_quality,
    table6_random_baseline,
)
from seqrefactor.model import (
    ComplexityRecord,
    DependencyMass,
    OperationCounters,
    RunReport,
    StepRecord,
    Verdict,
)
from seqrefactor.report import hypothesis_tests


def _run(subject: str, strategy: str) -> RunReport:
    step = StepRecord(index=0, smell="s0", verdict=Verdict(smell="s0", accepted=True, rationale="t"))
    return RunReport(subject=subject, strategy=strategy, generator="baseline", steps=[step])


def test_table2_ablation_writes_three_formats(tmp_path) -> None:
    runs = [_run("subj", "seqrefactor")]

    rows = table2_ablation(runs, out_dir=tmp_path)

    assert len(rows) == 1
    assert (tmp_path / "table2_ablation.csv").is_file()
    assert (tmp_path / "table2_ablation.tex").is_file()
    assert (tmp_path / "table2_ablation.md").is_file()
    assert "seqrefactor" in (tmp_path / "table2_ablation.csv").read_text()


def test_table3_depmass_writes_three_formats(tmp_path) -> None:
    masses = [
        DependencyMass(
            subject="pilot", positive_mass=0.6, negative_mass=0.25,
            co_resolution_events=0, cascading_violation_events=0,
        )
    ]

    rows = table3_depmass(masses, out_dir=tmp_path)

    assert rows[0]["mass_ratio"] > 0
    assert (tmp_path / "table3_depmass.tex").read_text().startswith("\\begin{table}")


def test_table4_efficiency_writes_three_formats(tmp_path) -> None:
    records = [
        ComplexityRecord(
            subject="synthetic_V10", step_index=0, strategy="incremental", module_size=10,
            counters=OperationCounters(vertex_touches=2, edge_touches=3), wall_clock_seconds=0.001,
        )
    ]

    rows = table4_efficiency(records, out_dir=tmp_path)

    assert rows[0]["edge_touches"] == 3
    assert (tmp_path / "table4_efficiency.md").is_file()


def test_summary_md_lists_every_hypothesis(tmp_path) -> None:
    from seqrefactor.eval.depmass import wilcoxon_h4

    runs = [_run("subj", "seqrefactor"), _run("subj", "unordered"), _run("subj", "topo_only")]
    h1_h3 = hypothesis_tests(runs)
    h4 = wilcoxon_h4([0.1, 0.2], [0.05, 0.1])

    summary_md(h1_h3, h4, out_dir=tmp_path)

    text = (tmp_path / "SUMMARY.md").read_text()
    assert "H1_fewer_cascading_violations_vs_unordered" in text
    assert "H4_dependency_mass" in text
    assert "H5" in text  # noted as proved by construction, not a statistical row


def test_table5_detector_quality_writes_three_formats(tmp_path) -> None:
    results = [
        DetectorQualityResult(
            subject="synth_small_low", ground_truth_count=8, detected_count=8,
            true_positives=8, precision=1.0, recall=1.0, f1=1.0,
        )
    ]
    rows = table5_detector_quality(results, out_dir=tmp_path)
    assert rows[0]["f1"] == 1.0
    assert (tmp_path / "table5_detector_quality.csv").is_file()
    assert (tmp_path / "table5_detector_quality.tex").is_file()


def test_table6_random_baseline_writes_three_formats(tmp_path) -> None:
    results = [
        RandomBaselineResult(
            subject="pilot_checkout_v1", n_samples=100, mean_violation_fraction=0.5,
            stdev_violation_fraction=0.1, mean_random_topological_objective=1.5,
            stdev_random_topological_objective=0.05, seqrefactor_objective=1.6,
        )
    ]
    rows = table6_random_baseline(results, out_dir=tmp_path)
    assert rows[0]["n_samples"] == 100
    assert (tmp_path / "table6_random_baseline.md").is_file()
