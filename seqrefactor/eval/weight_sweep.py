"""RQ4 weight-sensitivity sweep (Working Brief §6: "RQ4 sensitivity sweep over
the impact weights (alpha, beta, gamma) and the discount delta is scripted and
its output saved"). The README previously noted this as the one piece of the
config/CLI plumbing ("weight_sweep" on Config, already present) that had no
execution loop behind it; this module is that loop.

Runs the full orchestrator (not just the ordering step) because
cascading-violation count and net smell resolution are pipeline OUTCOMES that
depend on what gets generated and verified at each ordered position, not
properties of the order alone. Always uses the deterministic baseline
generator, never the LLM adapter: sensitivity to (alpha, beta, gamma) is the
question, and holding the generator fixed as a control is exactly what the
main ablation already does when isolating ordering effects
(``orchestrator._select_ordering``) -- it also keeps the sweep free and
exactly reproducible run to run, which an LLM-backed sweep would not be.
"""

from __future__ import annotations

from pathlib import Path

from seqrefactor.model import Config, ImpactWeights, WeightSweep
from seqrefactor.orchestrator import Orchestrator


def sweep_combinations(sweep: WeightSweep) -> list[ImpactWeights]:
    """Every (alpha, beta) pair from ``sweep`` with gamma = 1 - alpha - beta,
    skipping combinations where gamma would be negative (Eq. 1's own
    constraint: alpha, beta, gamma >= 0 and sum to 1)."""
    alphas = sweep.alpha or [ImpactWeights().alpha]
    betas = sweep.beta or [ImpactWeights().beta]
    combos: list[ImpactWeights] = []
    for alpha in alphas:
        for beta in betas:
            gamma = round(1.0 - alpha - beta, 10)
            if gamma < 0:
                continue
            combos.append(ImpactWeights(alpha=alpha, beta=beta, gamma=gamma))
    return combos


def run_weight_sweep(
    base_cfg: Config, subject_paths: list[Path], generator: str = "baseline"
) -> list[dict]:
    """Run the seqrefactor strategy over every subject at every weight
    combination in ``base_cfg.weight_sweep``, one row per (weights, subject).
    Requires the built jvm-sidecar for real test/metric verification, exactly
    like any other real orchestrator run (see jvm-sidecar/README.md)."""
    sweep = base_cfg.weight_sweep or WeightSweep()
    orchestrator = Orchestrator()
    rows: list[dict] = []

    for weights in sweep_combinations(sweep):
        cfg = base_cfg.model_copy(update={"impact_weights": weights})
        for path in subject_paths:
            report = orchestrator.run_one(path, cfg, strategy="seqrefactor", generator=generator)
            rows.append(
                {
                    "alpha": weights.alpha,
                    "beta": weights.beta,
                    "gamma": weights.gamma,
                    "subject": report.subject,
                    "cascading_violations": report.cascading_violations,
                    "net_smell_resolution": report.net_smell_resolution,
                    "ordering_validity": report.ordering_validity,
                }
            )
    return rows
