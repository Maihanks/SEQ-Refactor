"""Unit tests for eval/stats.py's shared paired-test procedure."""

from __future__ import annotations

from seqrefactor.eval.stats import paired_test


def test_insufficient_sample_reports_none_not_false() -> None:
    result = paired_test([1.0, 2.0], [0.5, 0.5])

    assert result.n == 2
    assert result.supported is None
    assert result.p_value is None
    assert "insufficient" in result.note


def test_clear_effect_is_detected_and_supported() -> None:
    a = [5.0, 6.0, 7.0, 8.0, 9.0]
    b = [1.0, 1.0, 1.0, 1.0, 1.0]

    result = paired_test(a, b, direction="greater")

    assert result.n == 5
    assert result.supported is True
    assert result.p_value is not None and result.p_value < 0.05
    assert result.effect_size_r == 1.0  # every difference positive: maximal rank-biserial
    assert result.mean_difference is not None and result.mean_difference > 0
    assert result.ci_low is not None and result.ci_high is not None
    assert result.ci_low <= result.mean_difference <= result.ci_high


def test_no_effect_is_not_supported() -> None:
    a = [1.0, 2.0, 1.0, 2.0, 1.0, 2.0]
    b = [1.0, 2.0, 1.0, 2.0, 1.0, 2.0]  # identical: zero difference throughout

    result = paired_test(a, b, direction="greater")

    assert result.supported is None  # degenerate (all-zero), not a false negative
    assert "degenerate" in result.note


def test_mismatched_lengths_raise() -> None:
    import pytest

    with pytest.raises(ValueError):
        paired_test([1.0, 2.0], [1.0])
