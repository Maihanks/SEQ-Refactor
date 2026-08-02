"""Accept/reject fusion (Software Specification §5.9, FR-10).

Fuses the three verification signals (metric delta, tests, architecture)
into a single Verdict. Hard gates first (tests, architecture), soft
threshold second (aggregate metric delta) -- mirrors the ordering
algorithm's own "safety before priority" discipline: a metric improvement
never overrides a failing test suite or a broken architectural constraint.
"""

from __future__ import annotations

from seqrefactor.model import Evidence, SmellId, Verdict


class Gate:
    """Implements the ``Gate`` contract (§5.9): ``decide(evidence) -> Verdict``."""

    def __init__(self, min_metric_improvement: float = -0.05) -> None:
        # A small negative tolerance is allowed: a transformation that is a wash on the
        # aggregate metric but passes tests and preserves architecture is still accepted,
        # since the primary evidence for behaviour preservation is the test suite.
        self.min_metric_improvement = min_metric_improvement

    def decide(self, smell: SmellId, evidence: Evidence) -> Verdict:
        if not evidence.tests_pass:
            return Verdict(smell=smell, accepted=False, rationale="test suite failed")
        if not evidence.arch_ok:
            return Verdict(
                smell=smell, accepted=False, rationale="architectural constraint violated"
            )

        m = evidence.metric
        aggregate = (m.cohesion + m.coupling + m.complexity + m.readability + m.architecture) / 5
        if aggregate < self.min_metric_improvement:
            return Verdict(
                smell=smell,
                accepted=False,
                rationale=f"aggregate metric delta {aggregate:.3f} below threshold {self.min_metric_improvement}",
            )

        return Verdict(
            smell=smell,
            accepted=True,
            rationale=f"tests pass, architecture ok, aggregate metric delta {aggregate:.3f}",
        )
