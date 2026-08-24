"""Unit tests for the accept/reject fusion gate (§5.9, FR-10)."""

from __future__ import annotations

from seqrefactor.gate import Gate
from seqrefactor.model import Evidence, MetricDelta


def _evidence(tests_pass=True, arch_ok=True, compile_errors=None, **metric_kwargs) -> Evidence:
    return Evidence(
        metric=MetricDelta(**metric_kwargs),
        tests_pass=tests_pass,
        arch_ok=arch_ok,
        compile_errors=compile_errors or [],
    )


def test_failing_tests_reject_regardless_of_metrics() -> None:
    verdict = Gate().decide(
        "s1", _evidence(tests_pass=False, cohesion=1.0, coupling=1.0, complexity=1.0)
    )
    assert verdict.accepted is False
    assert "test" in verdict.rationale.lower()
    assert verdict.reason == "test_failure"


def test_compile_errors_are_classified_separately_from_test_failure() -> None:
    """Working Brief Phase 2c §5: a candidate that never compiled never really
    ran the test suite, so it must not be lumped in with "test_failure"."""
    verdict = Gate().decide(
        "s1", _evidence(tests_pass=False, compile_errors=["cannot find symbol"])
    )
    assert verdict.accepted is False
    assert verdict.reason == "compile_failure"


def test_arch_violation_rejects_even_with_passing_tests_and_good_metrics() -> None:
    verdict = Gate().decide(
        "s1", _evidence(arch_ok=False, cohesion=1.0, coupling=1.0, complexity=1.0)
    )
    assert verdict.accepted is False
    assert "architect" in verdict.rationale.lower()
    assert verdict.reason == "architecture_failure"


def test_good_aggregate_metric_delta_is_accepted() -> None:
    verdict = Gate().decide(
        "s1",
        _evidence(coupling=0.5, complexity=0.5, cohesion=0.5, readability=0.5, architecture=0.5),
    )
    assert verdict.accepted is True


def test_strongly_negative_metric_delta_is_rejected() -> None:
    verdict = Gate().decide(
        "s1",
        _evidence(
            coupling=-0.9, complexity=-0.9, cohesion=-0.9, readability=-0.9, architecture=-0.9
        ),
    )
    assert verdict.accepted is False
    assert verdict.reason == "metric_regression"


def test_small_negative_wash_within_tolerance_is_still_accepted() -> None:
    verdict = Gate(min_metric_improvement=-0.05).decide(
        "s1", _evidence(coupling=-0.01, complexity=0.01, cohesion=0.0, readability=0.0, architecture=0.0)
    )
    assert verdict.accepted is True
