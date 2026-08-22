"""Unit tests for eval/complexity.py (Working Brief §4)."""

from __future__ import annotations

from seqrefactor.eval.complexity import run_scaling_study


def test_scaling_study_is_deterministic_given_a_fixed_seed() -> None:
    first = run_scaling_study(module_sizes=[8], max_steps_per_size=3, repeats=1, seed=42)
    second = run_scaling_study(module_sizes=[8], max_steps_per_size=3, repeats=1, seed=42)

    first_shape = [(r.subject, r.step_index, r.strategy, r.counters) for r in first]
    second_shape = [(r.subject, r.step_index, r.strategy, r.counters) for r in second]
    assert first_shape == second_shape


def test_incremental_touches_no_more_edges_than_from_scratch_on_a_larger_module() -> None:
    records = run_scaling_study(module_sizes=[40], max_steps_per_size=1, repeats=1, seed=7)
    scratch = next(r for r in records if r.strategy == "from_scratch")
    incremental = next(r for r in records if r.strategy == "incremental")

    assert incremental.counters.edge_touches <= scratch.counters.edge_touches


def test_records_carry_the_requested_module_size() -> None:
    records = run_scaling_study(module_sizes=[5, 15], max_steps_per_size=1, repeats=1, seed=1)
    sizes = {r.module_size for r in records}
    assert sizes == {5, 15}
