"""Unit tests for eval/detector_quality.py (Working Brief Phase 2c §4)."""

from __future__ import annotations

from seqrefactor.eval.detector_quality import compute_detector_quality, run_study


def test_generated_subject_has_near_perfect_precision_and_recall() -> None:
    result = compute_detector_quality("synth_small_low")
    assert result is not None
    assert result.precision >= 0.9
    assert result.recall >= 0.9


def test_subject_with_no_real_source_is_excluded_not_scored_zero() -> None:
    result = compute_detector_quality("billing_cycle_v1")
    assert result is None


def test_run_study_only_includes_subjects_with_real_source() -> None:
    results = run_study(["pilot_checkout_v1", "billing_cycle_v1", "notification_mixed_v1"])
    subjects = {r.subject for r in results}
    assert subjects == {"pilot_checkout_v1"}


def test_f1_is_the_harmonic_mean_of_precision_and_recall() -> None:
    result = compute_detector_quality("pilot_checkout_v1")
    assert result is not None
    if result.precision + result.recall > 0:
        expected_f1 = 2 * result.precision * result.recall / (result.precision + result.recall)
        assert abs(result.f1 - round(expected_f1, 4)) < 1e-9
