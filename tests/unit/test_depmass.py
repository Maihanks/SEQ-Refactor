"""Unit tests for eval/depmass.py (Working Brief §5 / RQ5, H4)."""

from __future__ import annotations

from seqrefactor.eval.depmass import dependency_mass_for_subject, run_study, wilcoxon_h4
from tests.support import graph_from_manifest, load_manifest


def test_dependency_mass_reads_pilot_injected_ground_truth() -> None:
    graph = graph_from_manifest(load_manifest("pilot_checkout_v1"))
    mass = dependency_mass_for_subject("pilot_checkout_v1", graph)

    assert mass.positive_mass == 0.6  # s5 -> s6
    assert mass.negative_mass == 0.25  # s3 -> s4
    assert mass.co_resolution_events == 0  # no run supplied
    assert mass.cascading_violation_events == 0


def test_mass_ratio_is_negative_over_positive() -> None:
    graph = graph_from_manifest(load_manifest("pilot_checkout_v1"))
    mass = dependency_mass_for_subject("pilot_checkout_v1", graph)

    assert abs(mass.mass_ratio - (0.25 / 0.6)) < 1e-9


def test_h4_reports_insufficient_data_below_minimum_subject_count() -> None:
    result = wilcoxon_h4([0.1, 0.2], [0.05, 0.1])

    assert result.supported is None
    assert result.p_value is None
    assert "too small" in result.note or "only" in result.note


def test_h4_runs_a_real_test_at_the_minimum_sample_size() -> None:
    avoided = [0.9, 0.8, 0.85, 0.95, 0.7]
    forgone = [0.1, 0.15, 0.2, 0.05, 0.3]

    result = wilcoxon_h4(avoided, forgone)

    assert result.n == 5
    assert result.p_value is not None
    assert result.effect_size_r is not None
    assert -1.0 <= result.effect_size_r <= 1.0


def test_run_study_returns_masses_and_h4_result_for_the_synthetic_corpus() -> None:
    entries = [
        (subject, graph_from_manifest(load_manifest(subject)), None)
        for subject in ("pilot_checkout_v1", "billing_cycle_v1", "notification_mixed_v1")
    ]

    masses, h4 = run_study(entries)

    assert len(masses) == 3
    assert h4.n == 3
    assert h4.supported is None  # below MIN_SUBJECTS_FOR_TEST: honest non-conclusion
