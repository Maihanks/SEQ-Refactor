"""Shared non-parametric paired-test utilities (paper §VII-D's methodology
reference [25], Wohlin et al.; Working Brief §5/§6). One reviewed statistical
procedure backs every hypothesis test in this repository: the main ablation's
H1-H3 (``report.hypothesis_tests``) and the dependency-mass study's H4
(``eval/depmass.wilcoxon_h4``) both call ``paired_test`` below, rather than
each hand-rolling its own Wilcoxon/effect-size/CI logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy import stats

MIN_N_FOR_TEST = 5  # below this, Wilcoxon signed-rank has essentially no power


@dataclass
class PairedTestResult:
    n: int
    statistic: float | None
    p_value: float | None
    effect_size_r: float | None  # matched-pairs rank-biserial correlation
    ci_low: float | None  # 95% bootstrap CI on the mean paired difference (a - b)
    ci_high: float | None
    mean_difference: float | None
    supported: bool | None  # None when the sample cannot support a conclusion either way
    note: str


def bootstrap_ci_mean_difference(
    a: list[float],
    b: list[float],
    confidence: float = 0.95,
    n_boot: int = 2000,
    seed: int = 20260101,
) -> tuple[float, float]:
    """Percentile bootstrap CI on the mean of ``a - b``, resampling paired
    differences with replacement -- standard practice for a paired
    non-parametric design where the sampling distribution of the mean
    difference has no convenient closed form."""
    rng = np.random.default_rng(seed)
    diffs = np.array(a) - np.array(b)
    boot_means = rng.choice(diffs, size=(n_boot, len(diffs)), replace=True).mean(axis=1)
    alpha = (1 - confidence) / 2
    return float(np.quantile(boot_means, alpha)), float(np.quantile(boot_means, 1 - alpha))


def paired_test(
    a: list[float],
    b: list[float],
    direction: Literal["greater", "less", "two-sided"] = "greater",
    min_n: int = MIN_N_FOR_TEST,
    confidence: float = 0.95,
    seed: int = 20260101,
) -> PairedTestResult:
    """Wilcoxon signed-rank paired test of ``a`` vs ``b`` (default alternative:
    ``a`` is stochastically greater than ``b``, matching this repo's H1-H4
    framing of "SEQ-REFACTOR/avoided-mass is better") plus a matched-pairs
    rank-biserial effect size and a percentile bootstrap CI on the mean
    paired difference.

    Returns ``supported=None`` (never ``False``) when the sample is too small
    or degenerate to support any conclusion: an underpowered non-result is a
    data-coverage gap, not evidence against the hypothesis (brief's own
    instruction, "report honestly ... a negative result is still a result" --
    which presupposes there was enough data to compute one).
    """
    n = len(a)
    if n != len(b):
        raise ValueError("paired samples must have equal length")

    if n < min_n:
        return PairedTestResult(
            n=n,
            statistic=None,
            p_value=None,
            effect_size_r=None,
            ci_low=None,
            ci_high=None,
            mean_difference=None,
            supported=None,
            note=(
                f"only {n} paired observation(s) (minimum {min_n} required); "
                "insufficient for a paired test -- a data-coverage gap, not a negative result."
            ),
        )

    diffs = np.array(a) - np.array(b)
    mean_difference = float(diffs.mean())
    ci_low, ci_high = bootstrap_ci_mean_difference(a, b, confidence, seed=seed)

    nonzero = diffs[diffs != 0]
    if len(nonzero) == 0:
        return PairedTestResult(
            n=n,
            statistic=None,
            p_value=None,
            effect_size_r=None,
            ci_low=ci_low,
            ci_high=ci_high,
            mean_difference=mean_difference,
            supported=None,
            note="every paired difference is exactly zero; the test is degenerate.",
        )

    statistic, p_value = stats.wilcoxon(a, b, alternative=direction, zero_method="wilcox")
    ranks = stats.rankdata(np.abs(nonzero))
    w_plus = ranks[nonzero > 0].sum()
    w_minus = ranks[nonzero < 0].sum()
    effect_size_r = (w_plus - w_minus) / (w_plus + w_minus)

    supported = bool(p_value < 0.05)
    note = f"{'supported' if supported else 'not supported'} at p<0.05 (H_alt: {direction})"

    return PairedTestResult(
        n=n,
        statistic=float(statistic),
        p_value=float(p_value),
        effect_size_r=float(effect_size_r),
        ci_low=ci_low,
        ci_high=ci_high,
        mean_difference=mean_difference,
        supported=supported,
        note=note,
    )
