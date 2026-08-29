"""Unit tests for the E2 quality-score sensitivity study (Working Brief Phase 4)."""

from __future__ import annotations

from seqrefactor.eval.quality_sensitivity import QUALITY_WEIGHT_VECTORS, table_quality_sensitivity
from seqrefactor.model import MetricDelta, RunReport, StepRecord, Verdict


def _run(subject: str, strategy: str, n_accepted: int, metric: MetricDelta) -> RunReport:
    steps = [
        StepRecord(
            index=i,
            smell=f"s{i}",
            verdict=Verdict(smell=f"s{i}", accepted=i < n_accepted, rationale="t"),
            metric=metric,
        )
        for i in range(5)
    ]
    return RunReport(subject=subject, strategy=strategy, generator="baseline", steps=steps)


def _five_subject_runs(seq_accepted: int, topo_accepted: int, metric: MetricDelta) -> list[RunReport]:
    runs = []
    for i in range(5):
        runs.append(_run(f"subj{i}", "seqrefactor", seq_accepted, metric))
        runs.append(_run(f"subj{i}", "topo_only", topo_accepted, metric))
    return runs


def test_table_has_one_row_per_weight_vector_and_score_mode() -> None:
    metric = MetricDelta(cohesion=0.5, coupling=0.5, complexity=0.5, readability=0.5, architecture=0.5)
    runs = _five_subject_runs(seq_accepted=5, topo_accepted=1, metric=metric)

    rows = table_quality_sensitivity(runs)

    # 1 "current" weight-vector (no weights, just the pre-existing measure) + every
    # entry in QUALITY_WEIGHT_VECTORS, each x 2 score modes (summed, normalised).
    expected_rows = (1 + len(QUALITY_WEIGHT_VECTORS)) * 2
    assert len(rows) == expected_rows

    weight_vectors_seen = {r["weight_vector"] for r in rows}
    assert weight_vectors_seen == {"current_accepted_count", *QUALITY_WEIGHT_VECTORS}

    modes_seen = {r["score_mode"] for r in rows}
    assert modes_seen == {"summed", "normalised"}


def test_conclusion_holds_across_every_weight_vector_when_advantage_is_real() -> None:
    """A genuine, uniform per-family improvement should show H3 supported under
    every quality-weight vector and both score modes -- there is nothing here that
    should make it weight-sensitive."""
    metric = MetricDelta(cohesion=1.0, coupling=1.0, complexity=1.0, readability=1.0, architecture=1.0)
    runs = _five_subject_runs(seq_accepted=5, topo_accepted=1, metric=metric)

    rows = table_quality_sensitivity(runs)

    assert all(r["supported"] is True for r in rows)


def test_conclusion_can_flip_under_a_weight_vector_that_isolates_a_regressed_family() -> None:
    """The brief's own acceptance check for E2: if a weighting exists under which the
    conclusion does not hold, the table must show that, not paper over it. Construct a
    metric delta where one family (readability) is WORSE for seqrefactor than
    topo_only while the rest are better, and confirm the readability/architecture-heavy
    vector reflects that, even though the equal-weighted vector still favours
    seqrefactor overall."""
    seq_metric = MetricDelta(
        cohesion=1.0, coupling=1.0, complexity=1.0, readability=-1.0, architecture=1.0
    )
    topo_metric = MetricDelta(
        cohesion=0.1, coupling=0.1, complexity=0.1, readability=1.0, architecture=0.1
    )
    runs = []
    for i in range(6):
        runs.append(_run(f"subj{i}", "seqrefactor", n_accepted=5, metric=seq_metric))
        runs.append(_run(f"subj{i}", "topo_only", n_accepted=5, metric=topo_metric))

    rows = table_quality_sensitivity(runs)
    by_key = {(r["weight_vector"], r["score_mode"]): r for r in rows}

    # Equal weighting: seqrefactor's four-family advantage outweighs the one regressed
    # family, so the conclusion should still hold.
    assert by_key[("equal", "summed")]["supported"] is True

    # A vector that weights readability/architecture heavily is dominated by the one
    # family where topo_only is actually better -- the conclusion should NOT hold there.
    assert by_key[("readability_architecture_heavy", "summed")]["supported"] is not True
