"""Unit tests for RunReport's GSR / rejection-reason computed properties
(Working Brief Phase 2c §5)."""

from __future__ import annotations

from seqrefactor.model import RunReport, StepRecord, Verdict


def _step(index: int, accepted: bool, reason: str) -> StepRecord:
    return StepRecord(
        index=index, smell=f"s{index}", verdict=Verdict(smell=f"s{index}", accepted=accepted, rationale="t", reason=reason)
    )


def test_generation_success_rate_excludes_only_no_patch_steps() -> None:
    steps = [
        _step(0, True, "accepted"),
        _step(1, False, "no_patch"),
        _step(2, False, "test_failure"),  # generation succeeded, gate rejected
        _step(3, False, "no_patch"),
    ]
    report = RunReport(subject="s", strategy="seqrefactor", generator="baseline", steps=steps)

    assert report.generation_attempts == 4
    assert report.successful_generations == 2  # index 0 and 2
    assert report.generation_success_rate == 0.5


def test_generation_success_rate_is_zero_with_no_steps() -> None:
    report = RunReport(subject="s", strategy="seqrefactor", generator="baseline", steps=[])
    assert report.generation_success_rate == 0.0


def test_rejection_reason_counts_excludes_accepted_steps() -> None:
    steps = [
        _step(0, True, "accepted"),
        _step(1, False, "no_patch"),
        _step(2, False, "no_patch"),
        _step(3, False, "compile_failure"),
        _step(4, False, "test_failure"),
    ]
    report = RunReport(subject="s", strategy="seqrefactor", generator="baseline", steps=steps)

    assert report.rejection_reason_counts == {"no_patch": 2, "compile_failure": 1, "test_failure": 1}


def test_nsr_rate_given_generation_success_normalises_by_successful_attempts() -> None:
    steps = [_step(0, True, "accepted"), _step(1, False, "no_patch"), _step(2, False, "no_patch")]
    report = RunReport(subject="s", strategy="seqrefactor", generator="baseline", steps=steps)

    # 1 accepted, 0 introduced => NSR = 1; only 1 of 3 steps had a real generation attempt
    assert report.net_smell_resolution == 1
    assert report.successful_generations == 1
    assert report.net_smell_resolution_rate_given_generation_success == 1.0


def test_nsr_rate_given_generation_success_is_zero_when_generation_never_succeeds() -> None:
    steps = [_step(0, False, "no_patch"), _step(1, False, "no_patch")]
    report = RunReport(subject="s", strategy="seqrefactor", generator="baseline", steps=steps)
    assert report.net_smell_resolution_rate_given_generation_success == 0.0
