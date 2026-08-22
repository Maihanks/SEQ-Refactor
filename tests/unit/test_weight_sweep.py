"""Unit tests for eval/weight_sweep.py's pure combination logic (Working Brief
§6, RQ4). ``run_weight_sweep`` itself drives the real orchestrator and needs
the built jvm-sidecar; it is exercised via the CLI/`make results` path, not
unit-tested here (matching this repo's existing convention for
sidecar-dependent code, see tests/unit/test_verify_sidecar.py).
"""

from __future__ import annotations

from seqrefactor.eval.weight_sweep import sweep_combinations
from seqrefactor.model import WeightSweep


def test_sweep_combinations_covers_the_full_cross_product() -> None:
    sweep = WeightSweep(alpha=[0.2, 0.4], beta=[0.2, 0.4])

    combos = sweep_combinations(sweep)

    assert len(combos) == 4
    assert all(abs(c.alpha + c.beta + c.gamma - 1.0) < 1e-9 for c in combos)


def test_sweep_combinations_skips_negative_gamma() -> None:
    sweep = WeightSweep(alpha=[0.6], beta=[0.6])  # alpha + beta > 1: gamma would be negative

    combos = sweep_combinations(sweep)

    assert combos == []


def test_sweep_combinations_falls_back_to_default_weight_when_axis_unset() -> None:
    sweep = WeightSweep(alpha=[0.5], beta=[])

    combos = sweep_combinations(sweep)

    assert len(combos) == 1
    assert combos[0].alpha == 0.5
