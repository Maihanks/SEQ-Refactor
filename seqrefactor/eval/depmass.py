"""The dependency-mass study (Working Brief §5 / C7; RQ5, H4).

H4 (as reframed by the brief, not the supervisor's original inequality):
across subjects, does the *avoided* negative (cascading) mass -- negative
mass whose cascade dependency-aware ordering actually prevented -- differ
from the *forgone* positive (co-resolution) mass -- positive mass whose
co-resolution opportunity was not realised? This operationalisation is
necessary because only aggregate outcomes are observable from a
:class:`~seqrefactor.model.RunReport` (which smells were accepted, and the
paper's own Definition-2 cascading-violation count), not a per-edge
realisation trace, so a rate is estimated per polarity and applied to that
polarity's total mass:

    avoided_negative_mass = negative_mass * (1 - cascading_violation_rate)
    forgone_positive_mass = positive_mass * (1 - co_resolution_rate)

    cascading_violation_rate = cascading_violation_events / |negative edges|
    co_resolution_rate       = co_resolution_events / |positive edges|

HONESTY NOTE (also stated on ``model.DependencyMass``): the positive/negative
probabilities behind this mass are seeded catalogue defaults
(``graph/rules.py``), not mined from version histories -- this measures a
modelled distribution, not an observed one. See that module's docstring for
the full note. State this alongside any H4 result reported from here.
"""

from __future__ import annotations

from dataclasses import dataclass

from seqrefactor.eval.stats import MIN_N_FOR_TEST, paired_test
from seqrefactor.model import DependencyMass, RunReport, SmellDependencyGraph

MIN_SUBJECTS_FOR_TEST = MIN_N_FOR_TEST


@dataclass
class H4Result:
    n: int
    statistic: float | None
    p_value: float | None
    effect_size_r: float | None  # matched-pairs rank-biserial correlation
    supported: bool | None  # None when the data cannot support a conclusion either way
    note: str


def dependency_mass_for_subject(
    subject: str, graph: SmellDependencyGraph, run: RunReport | None = None
) -> DependencyMass:
    """Structural mass always; realised co-resolution/cascading counts only if
    ``run`` (an executed :class:`RunReport`) is supplied."""
    positive_edges = [e for e in graph.edges if e.polarity == "positive"]
    negative_edges = [e for e in graph.edges if e.polarity == "negative"]

    co_resolution_events = 0
    cascading_violation_events = 0
    if run is not None:
        accepted = {s.smell for s in run.steps if s.verdict.accepted}
        co_resolution_events = sum(1 for e in positive_edges if e.src in accepted and e.dst in accepted)
        cascading_violation_events = run.cascading_violations

    return DependencyMass(
        subject=subject,
        positive_mass=sum(e.probability for e in positive_edges),
        negative_mass=sum(e.probability for e in negative_edges),
        co_resolution_events=co_resolution_events,
        cascading_violation_events=cascading_violation_events,
    )


def _avoided_and_forgone(
    graph: SmellDependencyGraph, mass: DependencyMass
) -> tuple[float, float]:
    positive_edges = [e for e in graph.edges if e.polarity == "positive"]
    negative_edges = [e for e in graph.edges if e.polarity == "negative"]

    co_rate = mass.co_resolution_events / len(positive_edges) if positive_edges else 0.0
    casc_rate = mass.cascading_violation_events / len(negative_edges) if negative_edges else 0.0

    avoided_negative = mass.negative_mass * (1 - casc_rate)
    forgone_positive = mass.positive_mass * (1 - co_rate)
    return avoided_negative, forgone_positive


def wilcoxon_h4(avoided_negative: list[float], forgone_positive: list[float]) -> H4Result:
    """H4 as a paired test of avoided-negative-mass > forgone-positive-mass,
    via the shared ``eval.stats.paired_test`` procedure (Wilcoxon signed-rank
    + rank-biserial effect size + bootstrap CI)."""
    result = paired_test(
        avoided_negative, forgone_positive, direction="greater", min_n=MIN_SUBJECTS_FOR_TEST
    )
    note = result.note
    if result.n < MIN_SUBJECTS_FOR_TEST:
        note = (
            f"only {result.n} subject(s) available (minimum {MIN_SUBJECTS_FOR_TEST} to run "
            "the paired test at all); the corpus in this increment (three synthetic "
            "subjects, see REPO_MAP.md) is too small for a statistical H4 conclusion "
            "-- this is a data-coverage gap, not a negative result."
        )
    return H4Result(
        n=result.n,
        statistic=result.statistic,
        p_value=result.p_value,
        effect_size_r=result.effect_size_r,
        supported=result.supported,
        note=note,
    )


def run_study(
    entries: list[tuple[str, SmellDependencyGraph, RunReport | None]],
) -> tuple[list[DependencyMass], H4Result]:
    """Compute per-subject :class:`DependencyMass` rows and the H4 test across
    them, from (subject, ground-truth-or-built graph, optional run) triples."""
    masses: list[DependencyMass] = []
    avoided: list[float] = []
    forgone: list[float] = []

    for subject, graph, run in entries:
        mass = dependency_mass_for_subject(subject, graph, run)
        masses.append(mass)
        a, f = _avoided_and_forgone(graph, mass)
        avoided.append(a)
        forgone.append(f)

    return masses, wilcoxon_h4(avoided, forgone)
